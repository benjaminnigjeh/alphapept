# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/07_recalibration.ipynb (unless otherwise specified).

__all__ = ['remove_outliers', 'transform', 'kneighbors_calibration', 'get_calibration', 'calibrate_hdf',
           'get_db_targets', 'align_run_to_db', 'calibrate_fragments']

# Cell

import numpy as np
import pandas as pd

def remove_outliers(
    df:  pd.DataFrame,
    outlier_std: float) -> pd.DataFrame:
    """Helper function to remove outliers from a dataframe.
    Outliers are removed based on the precursor offset mass (prec_offset).
    All values within x standard deviations to the median are kept.

    Args:
        df (pd.DataFrame): Input dataframe that contains a prec_offset_ppm-column.
        outlier_std (float): Range of standard deviations to filter outliers

    Raises:
        ValueError: An error if the column is not present in the dataframe.

    Returns:
        pd.DataFrame: A dataframe w/o outliers.
    """

    if 'prec_offset_ppm' not in df.columns:
        raise ValueError(f"Column prec_offset_ppm not in df")
    else:
        # Remove outliers for calibration
        o_mass_std = np.abs(df['prec_offset_ppm'].std())
        o_mass_median = df['prec_offset_ppm'].median()

        df_sub = df.query('prec_offset_ppm < @o_mass_median+@outlier_std*@o_mass_std and prec_offset_ppm > @o_mass_median-@outlier_std*@o_mass_std').copy()

        return df_sub

# Cell

def transform(
    x:  np.ndarray,
    column: str,
    scaling_dict: dict) -> np.ndarray:
    """Helper function to transform an input array for neighbors lookup used for calibration

    Note: The scaling_dict stores information about how scaling is applied and is defined in get_calibration

    Relative transformation: Compare distances relatively, for mz that is ppm, for mobility %.
    Absolute transformation: Compare distance absolute, for RT it is the timedelta.

    An example definition is below:

    scaling_dict = {}
    scaling_dict['mz'] = ('relative', calib_mz_range/1e6)
    scaling_dict['rt'] = ('absolute', calib_rt_range)
    scaling_dict['mobility'] = ('relative', calib_mob_range)

    Args:
        x (np.ndarray): Input array.
        column (str): String to lookup what scaling should be applied.
        scaling_dict (dict): Lookup dict to retrieve the scaling operation and factor for the column.

    Raises:
        KeyError: An error if the column is not present in the dict.
        NotImplementedError: An error if the column is not present in the dict.

    Returns:
        np.ndarray: A scaled array.
    """
    if column not in scaling_dict:
        raise KeyError(f"Column {_} not in scaling_dict")
    else:
        type_, scale_ = scaling_dict[column]

        if type_ == 'relative':
            return np.log(x, out=np.zeros_like(x), where=(x>0))/scale_
        elif type_ == 'absolute':
            return x/scale_
        else:
            raise NotImplementedError(f"Type {type_} not known.")

# Cell

from sklearn.neighbors import KNeighborsRegressor


def kneighbors_calibration(df: pd.DataFrame, features: pd.DataFrame, cols: list, target: str, scaling_dict: dict, calib_n_neighbors: int) -> np.ndarray:
    """Calibration using a KNeighborsRegressor.
    Input arrays from are transformed to be used with a nearest-neighbor approach.
    Based on neighboring points a calibration is calculated for each input point.

    Args:
        df (pd.DataFrame): Input dataframe that contains identified peptides (w/o outliers).
        features (pd.DataFrame): Features dataframe for which the masses are calibrated.
        cols (list): List of input columns for the calibration.
        target (str): Target column on which offset is calculated.
        scaling_dict (dict): A dictionary that contains how scaling operations are applied.
        calib_n_neighbors (int): Number of neighbors for calibration.

    Returns:
        np.ndarray: A numpy array with calibrated masses.
    """

    data = df[cols]
    tree_points = data.values

    for idx, _ in enumerate(data.columns):
        tree_points[:, idx] = transform(tree_points[:, idx], _, scaling_dict)

    target_points = features[[_+'_matched' for _ in cols]].values

    for idx, _ in enumerate(data.columns):
        target_points[:, idx] = transform(target_points[:, idx], _, scaling_dict)

    neigh = KNeighborsRegressor(n_neighbors=calib_n_neighbors, weights = 'distance')
    neigh.fit(tree_points, df[target].values)

    y_hat = neigh.predict(target_points)

    return y_hat

# Cell
import logging

def get_calibration(
    df: pd.DataFrame,
    features:pd.DataFrame,
    outlier_std: float = 3,
    calib_n_neighbors: int = 100,
    calib_mz_range: int = 20,
    calib_rt_range: float = 0.5,
    calib_mob_range: float = 0.3,
    **kwargs) -> (np.ndarray, float):
    """Wrapper function to get calibrated values for the precursor mass.

    Args:
        df (pd.DataFrame): Input dataframe that contains identified peptides.
        features (pd.DataFrame): Features dataframe for which the masses are calibrated.
        outlier_std (float, optional): Range in standard deviations for outlier removal. Defaults to 3.
        calib_n_neighbors (int, optional): Number of neighbors used for regression. Defaults to 100.
        calib_mz_range (int, optional): Scaling factor for mz range. Defaults to 20.
        calib_rt_range (float, optional): Scaling factor for rt_range. Defaults to 0.5.
        calib_mob_range (float, optional): Scaling factor for mobility range. Defaults to 0.3.
        **kwargs: Arbitrary keyword arguments so that settings can be passes as whole.


    Returns:
        corrected_mass (np.ndarray): The calibrated mass
        y_hat_std (float): The standard deviation of the precursor offset after calibration

    """

    if len(df) > calib_n_neighbors:

        target = 'prec_offset_ppm'
        cols = ['mz','rt']

        if 'mobility' in df.columns:
            cols += ['mobility']

        scaling_dict = {}
        scaling_dict['mz'] = ('relative', calib_mz_range/1e6)
        scaling_dict['rt'] = ('absolute', calib_rt_range)
        scaling_dict['mobility'] = ('relative', calib_mob_range)

        df_sub = remove_outliers(df, outlier_std)
        y_hat = kneighbors_calibration(df, features, cols, target, scaling_dict, calib_n_neighbors)

        corrected_mass = (1-y_hat/1e6) * features['mass_matched']

        y_hat_std = y_hat.std()

        mad_offset = np.median(np.absolute(y_hat - np.median(y_hat)))

        return corrected_mass, y_hat_std, mad_offset


    else:
        logging.info('Not enough data points present. Skipping recalibration.')
        return features['mass_matched'], np.abs(df['prec_offset_ppm'].std())

# Cell

from typing import Union
import alphapept.io
from .score import score_x_tandem
import os


def calibrate_hdf(
    to_process: tuple, callback=None, parallel=True) -> Union[str,bool]:
    """Wrapper function to get calibrate a hdf file when using the parallel executor.
    The function loads the respective dataframes from the hdf, calls the calibration function and applies the offset.

    Args:
        to_process (tuple): Tuple that contains the file index and the settings dictionary.
        callback ([type], optional): Placeholder for callback (unused).
        parallel (bool, optional): Placeholder for parallel usage (unused).

    Returns:
        Union[str,bool]: Either True as boolean when calibration is successfull or the Error message as string.
    """

    try:
        index, settings = to_process
        file_name = settings['experiment']['file_paths'][index]
        base_file_name, ext = os.path.splitext(file_name)
        ms_file = base_file_name+".ms_data.hdf"
        ms_file_ = alphapept.io.MS_Data_File(ms_file, is_overwritable=True)

        features = ms_file_.read(dataset_name='features')

        try:
            psms =  ms_file_.read(dataset_name='first_search')
        except KeyError: #no elements in search
            psms = pd.DataFrame()

        if len(psms) > 0 :
            df = score_x_tandem(
                psms,
                fdr_level=settings["search"]["peptide_fdr"],
                plot=False,
                verbose=False,
                **settings["search"]
            )
            corrected_mass, std, prec_offset_ppm_std = get_calibration(
                df,
                features,
                **settings["calibration"]
            )
            ms_file_.write(
                corrected_mass,
                dataset_name="corrected_mass",
                group_name="features"
            )
        else:

            ms_file_.write(
                features['mass_matched'],
                dataset_name="corrected_mass",
                group_name="features"
            )

            prec_offset_ppm_std = 0

        ms_file_.write(
            prec_offset_ppm_std,
            dataset_name="corrected_mass",
            group_name="features",
            attr_name="estimated_max_precursor_ppm"
        )
        logging.info(f'Calibration of file {ms_file} complete.')


        # Calibration of fragments

        skip = False

        try:
            logging.info(f'Calibrating fragments')
            ions = ms_file_.read(dataset_name='ions')
        except KeyError:
            logging.info('No ions to calibrate fragment masses found')

            skip = True

        if not skip:
            delta_ppm = ((ions['db_mass'] - ions['ion_mass'])/((ions['db_mass'] + ions['ion_mass'])/2)*1e6).values
            median_offset = -np.median(delta_ppm)
            std_offset = np.std(delta_ppm)
            mad_offset = np.median(np.absolute(delta_ppm - np.median(delta_ppm)))

            mass_list_ms2 = ms_file_.read(dataset_name = 'mass_list_ms2', group_name = "Raw/MS2_scans")

            try:
                offset = ms_file_.read(dataset_name = 'corrected_fragment_mzs')
            except KeyError:
                offset = np.zeros(len(mass_list_ms2))

            offset += median_offset

            logging.info(f'Median fragment offset {median_offset:.2f} - std {std_offset:.2f} ppm - mad {mad_offset:.2f} ppm')

            ms_file_.write(
                offset,
                dataset_name="corrected_fragment_mzs",
            )

            ms_file_.write(np.array([mad_offset]), dataset_name="estimated_max_fragment_ppm")

        return True
    except Exception as e:
        logging.error(f'Calibration of file {ms_file} failed. Exception {e}.')
        return f"{e}" #Can't return exception object, cast as string

# Cell

import scipy.stats
import scipy.signal
import scipy.interpolate
import alphapept.fasta

#The following function does not have an own unit test but is run by test_calibrate_fragments.
def get_db_targets(
    db_file_name: str,
    max_ppm: int=100,
    min_distance: float=0.5,
    ms_level: int=2,
) ->np.ndarray:
    """Function to extract database targets for database-calibration.
    Based on the FASTA database it finds masses that occur often. These will be used for calibration.


    Args:
        db_file_name (str): Path to the database.
        max_ppm (int, optional): Maximum distance in ppm between two peaks. Defaults to 100.
        min_distance (float, optional): Minimum distance between two calibration peaks. Defaults to 0.5.
        ms_level (int, optional): MS-Level used for calibration, either precursors (1) or fragmasses (2). Defaults to 2.

    Raises:
        ValueError: When ms_level is not valid.

    Returns:
        np.ndarray: Numpy array with calibration masses.
    """

    if ms_level == 1:
        db_mzs_ = alphapept.fasta.read_database(db_file_name, 'precursors')
    elif ms_level == 2:
        db_mzs_ = alphapept.fasta.read_database(db_file_name, 'fragmasses')
    else:
        raise ValueError(f"{ms_level} is not a valid ms level")
    tmp_result = np.bincount(
        (
            np.log10(
                db_mzs_[
                    np.isfinite(db_mzs_) & (db_mzs_ > 0)
                ].flatten()
            ) * 10**6
        ).astype(np.int64)
    )
    db_mz_distribution = np.zeros_like(tmp_result)
    for i in range(1, max_ppm):
        db_mz_distribution[i:] += tmp_result[:-i]
        db_mz_distribution[:-i] += tmp_result[i:]
    peaks = scipy.signal.find_peaks(db_mz_distribution, distance=max_ppm)[0]
    db_targets = 10 ** (peaks / 10**6)
    db_array = np.zeros(int(db_targets[-1]) + 1, dtype=np.float64)
    last_int_mz = -1
    last_mz = -1
    for mz in db_targets:
        mz_int = int(mz)
        if (mz_int != last_int_mz) & (mz > (last_mz + min_distance)):
            db_array[mz_int] = mz
        else:
            db_array[mz_int] = 0
        last_int_mz = mz_int
        last_mz = mz
    return db_array

# Cell

#The following function does not have an own unit test but is run by test_calibrate_fragments.
def align_run_to_db(
    ms_data_file_name: str,
    db_array: np.ndarray,
    max_ppm_distance: int=1000000,
    rt_step_size:float =0.1,
    plot_ppms: bool=False,
    ms_level: int=2,
) ->np.ndarray:
    """Function align a run to it's theoretical FASTA database.

    Args:
        ms_data_file_name (str): Path to the run.
        db_array (np.ndarray): Numpy array containing the database targets.
        max_ppm_distance (int, optional): Maximum distance in ppm. Defaults to 1000000.
        rt_step_size (float, optional): Stepsize for rt calibration. Defaults to 0.1.
        plot_ppms (bool, optional): Flag to indicate plotting. Defaults to False.
        ms_level (int, optional): ms_level for calibration. Defaults to 2.

    Raises:
        ValueError: When ms_level is not valid.

    Returns:
        np.ndarray: Estimated errors
    """

    ms_data = alphapept.io.MS_Data_File(ms_data_file_name)
    if ms_level == 1:
        mzs = ms_data.read(dataset_name="mass_matched", group_name="features")
        rts = ms_data.read(dataset_name="rt_matched", group_name="features")
    elif ms_level == 2:
        mzs = ms_data.read(dataset_name="Raw/MS2_scans/mass_list_ms2")
        inds = ms_data.read(dataset_name="Raw/MS2_scans/indices_ms2")
        precursor_rts = ms_data.read(dataset_name="Raw/MS2_scans/rt_list_ms2")
        rts = np.repeat(precursor_rts, np.diff(inds))
    else:
        raise ValueError(f"{ms_level} is not a valid ms level")

    selected = mzs.astype(np.int64)
    ds = np.zeros((3, len(selected)))
    if len(db_array) < len(selected) + 1:
        tmp = np.zeros(len(selected) + 1)
        tmp[:len(db_array)] = db_array
        db_array = tmp
    ds[0] = mzs - db_array[selected - 1]
    ds[1] = mzs - db_array[selected]
    ds[2] = mzs - db_array[selected + 1]
    min_ds = np.take_along_axis(
        ds,
        np.expand_dims(np.argmin(np.abs(ds), axis=0), axis=0),
        axis=0
    ).squeeze(axis=0)
    ppm_ds = min_ds / mzs * 10**6

    selected = np.abs(ppm_ds) < max_ppm_distance
    selected &= np.isfinite(rts)
    rt_order = np.argsort(rts)
    rt_order = rt_order[selected[rt_order]]


    ordered_rt = rts[rt_order]
    ordered_ppm = ppm_ds[rt_order]

    rt_idx_break = np.searchsorted(
        ordered_rt,
        np.arange(ordered_rt[0], ordered_rt[-1], rt_step_size),
        "left"
    )
    median_ppms = np.empty(len(rt_idx_break) - 1)
    for i in range(len(median_ppms)):
        median_ppms[i] = np.median(
            ordered_ppm[rt_idx_break[i]: rt_idx_break[i + 1]]
        )

    if plot_ppms:
        import matplotlib.pyplot as plt
        plt.plot(
            rt_step_size + np.arange(
                ordered_rt[0],
                ordered_rt[-1],
                rt_step_size
            )[:-1],
            median_ppms
        )
        plt.show()

    estimated_errors = scipy.interpolate.griddata(
        rt_step_size / 2 + np.arange(
            ordered_rt[0],
            ordered_rt[-1] - 2 * rt_step_size,
            rt_step_size
        ),
        median_ppms,
        rts,
        fill_value=0,
        method="linear",
        rescale=True
    )

    estimated_errors[~np.isfinite(estimated_errors)] = 0

    return estimated_errors

# Cell

def calibrate_fragments(
    db_file_name: str,
    ms_data_file_name: str,
    ms_level: int=2,
    write = True,
    plot_ppms = False,
):
    """Wrapper function to calibrate fragments.
    Calibrated values are saved to corrected_fragment_mzs

    Args:
        db_file_name (str): Path to database
        ms_data_file_name (str): Path to ms_data file
        ms_level (int, optional): MS-level for calibration. Defaults to 2.
        write (bool, optional): Boolean flag for test purposes to avoid writing to testfile. Defaults to True.
        plot_ppms (bool, optional):  Boolean flag to plot the calibration. Defaults to False.
    """

    db_array = get_db_targets(
        db_file_name,
        max_ppm=100,
        min_distance=0.5,
        ms_level=ms_level,
    )
    estimated_errors = align_run_to_db(
        ms_data_file_name,
        db_array=db_array,
        ms_level=ms_level,
        plot_ppms=plot_ppms,
    )

    if write:
        ms_file = alphapept.io.MS_Data_File(ms_data_file_name, is_overwritable=True)
        ms_file.write(
            estimated_errors,
            dataset_name="corrected_fragment_mzs",
        )