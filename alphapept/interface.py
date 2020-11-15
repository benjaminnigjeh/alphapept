# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/11_interface.ipynb (unless otherwise specified).

__all__ = ['tqdm_wrapper', 'set_logger', 'check_version_and_hardware', 'create_database', 'import_raw_data',
           'feature_finding', 'search_data', 'recalibrate_data', 'score', 'align', 'match', 'lfq_quantification',
           'export', 'run_complete_workflow', 'run_cli', 'cli_overview', 'cli_database', 'cli_import',
           'cli_feature_finding', 'cli_search', 'cli_recalibrate', 'cli_score', 'cli_align', 'cli_match',
           'cli_quantify', 'cli_export', 'cli_workflow', 'cli_gui', 'CONTEXT_SETTINGS', 'CLICK_SETTINGS_OPTION']

# Cell

import tqdm


def tqdm_wrapper(pbar, update):
    current_value = pbar.n
    delta = update - current_value
    pbar.update(delta)

# Cell

import logging
import sys


def set_logger():
    root = logging.getLogger()
    while root.hasHandlers():
        root.removeHandler(root.handlers[0])
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)-s - %(message)s', "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

# Cell

import alphapept.utils


def check_version_and_hardware(settings):
    alphapept.utils.check_hardware()
    alphapept.utils.check_python_env()
    settings = alphapept.utils.check_settings(settings)
    return settings

# Cell

import alphapept.fasta
import os
import functools


def create_database(
    settings,
    logger_set=False,
    settings_parsed=False,
    callback=None
):
    if not logger_set:
        set_logger()
    if not settings_parsed:
        settings = check_version_and_hardware(settings)
    if 'database_path' not in settings['fasta']:
        database_path = ''
    else:
        database_path = settings['fasta']['database_path']
    if settings['fasta']['save_db']:
        if os.path.isfile(database_path):
            logging.info(
                'Database path set and exists. Using {} as database.'.format(
                    database_path
                )
            )
        else:
            logging.info(
                'Database path {} is not a file.'.format(database_path)
            )

            if len(settings['fasta']['fasta_paths']) == 0:
                raise FileNotFoundError("No FASTA files set.")

            for fasta_file in settings['fasta']['fasta_paths']:
                if os.path.isfile(fasta_file):
                    logging.info(
                        'Found FASTA file {} with size {:.2f} Mb.'.format(
                            fasta_file,
                            os.stat(fasta_file).st_size/(1024**2)
                        )
                    )
                else:
                    raise FileNotFoundError(
                        'File {} not found'.format(fasta_file)
                    )

            logging.info('Creating a new database from FASTA.')

            if not callback:
                cb = functools.partial(tqdm_wrapper, tqdm.tqdm(total=1))
            else:
                cb = callback

            (
                spectra,
                pept_dict,
                fasta_dict
            ) = alphapept.fasta.generate_database_parallel(
                settings,
                callback=cb
            )
            logging.info(
                'Digested {:,} proteins and generated {:,} spectra'.format(
                    len(fasta_dict),
                    len(spectra)
                )
            )

            alphapept.fasta.save_database(
                spectra,
                pept_dict,
                fasta_dict,
                **settings['fasta']
            )
            logging.info(
                'Database saved to {}. Filesize of database is {:.2f} GB'.format(
                    database_path,
                    os.stat(database_path).st_size/(1024**3)
                )
            )

            settings['fasta']['database_path'] = database_path

    else:
        logging.info(
            'Not using a stored database. Create database on the fly.'
        )
    return settings

# Cell

import alphapept.io


def import_raw_data(
    settings,
    logger_set=False,
    settings_parsed=False,
    callback=None
):
    if not logger_set:
        set_logger()
    if not settings_parsed:
        settings = check_version_and_hardware(settings)
    files_ms_data_hdf = []
    to_convert = []

    for file_name in settings['experiment']['file_paths']:
        base, ext = os.path.splitext(file_name)
        ms_data_file_path = f'{base}.ms_data.hdf'
        files_ms_data_hdf.append(ms_data_file_path)
        if os.path.isfile(ms_data_file_path):
            logging.info(f'Found *.ms_data.hdf file for {file_name}')
        else:
            to_convert.append(file_name)
            logging.info(f'No *.ms_data.hdf file found for {file_name}. Adding to conversion list.')
    files_ms_data_hdf.sort()

    if len(to_convert) > 0:
        logging.info('Starting file conversion.')
        if not callback:
            cb = functools.partial(tqdm_wrapper, tqdm.tqdm(total=1))
        else:
            cb = callback
        alphapept.io.raw_to_ms_data_file_parallel(to_convert, settings)
        logging.info('File conversion complete.')
    return settings

# Cell

import alphapept.feature_finding


def feature_finding(
    settings,
    logger_set=False,
    settings_parsed=False,
    callback=None
):
    if not logger_set:
        set_logger()
    if not settings_parsed:
        settings = check_version_and_hardware(settings)
    to_convert = []
    for file_name in settings['experiment']['file_paths']:
        base, ext = os.path.splitext(file_name)
        hdf_path = base+'.ms_data.hdf'

        if os.path.isfile(hdf_path):
            try:
                alphapept.io.MS_Data_File(
                    hdf_path
                ).read(dataset_name="features")
                logging.info(
                    'Found *.hdf with features for {}'.format(file_name)
                )
            except KeyError:
                to_convert.append(file_name)
                logging.info(
                    'No *.hdf file with features found for {}. Adding to feature finding list.'.format(file_name)
                )
        else:
            to_convert.append(file_name)
            logging.info(
                'No *.hdf file with features found for {}. Adding to feature finding list.'.format(file_name)
            )

    if len(to_convert) > 0:
        logging.info(
            'Feature extraction for {} file(s).'.format(len(to_convert))
        )
        if not callback:
            cb = functools.partial(tqdm_wrapper, tqdm.tqdm(total=1))
        else:
            cb = callback

        alphapept.feature_finding.find_and_save_features_parallel(
            to_convert,
            settings,
            callback=cb
        )
    return settings

# Cell

import alphapept.search
import alphapept.io


def search_data(
    settings,
    recalibrated=False,
    logger_set=False,
    settings_parsed=False,
    callback=None
):
    if not logger_set:
        set_logger()
    if not settings_parsed:
        settings = check_version_and_hardware(settings)
    if not recalibrated:
        if settings['fasta']['save_db']:
            logging.info('Starting first search with DB.')

            if not callback:
                cb = functools.partial(tqdm_wrapper, tqdm.tqdm(total=1))
            else:
                cb = callback

            fasta_dict, pept_dict = alphapept.search.search_parallel_db(
                settings,
                callback=cb
            )

        else:
            logging.info('Starting first search.')

            if not callback:
                cb = functools.partial(tqdm_wrapper, tqdm.tqdm(total=1))
            else:
                cb = callback

            fasta_dict = alphapept.search.search_parallel(settings, callback=cb)
            pept_dict = None

        logging.info('First search complete.')
    else:
        ms_files = []
        for _ in settings['experiment']['file_paths']:
            base, ext = os.path.splitext(_)
            ms_files.append(base + '.ms_data.hdf')
        offsets = [
            alphapept.io.MS_Data_File(
                ms_file_name
            ).read(
                dataset_name="corrected_mass",
                group_name="features",
                attr_name="estimated_max_precursor_ppm"
            ) * settings['search']['calibration_std'] for ms_file_name in ms_files
        ]
        if settings['fasta']['save_db']:
            logging.info('Starting second search with DB.')

            if not callback:
                cb = functools.partial(tqdm_wrapper, tqdm.tqdm(total=1))
            else:
                cb = callback

            fasta_dict, pept_dict = alphapept.search.search_parallel_db(
                settings,
                calibration=offsets,
                callback=cb
            )

        else:
            logging.info('Starting second search.')

            if not callback:
                cb = functools.partial(tqdm_wrapper, tqdm.tqdm(total=1))
            else:
                cb = callback

            fasta_dict = alphapept.search.search_parallel(
                settings,
                calibration=offsets,
                callback=cb
            )
            pept_dict = None

        logging.info('Second search complete.')
    return settings, pept_dict, fasta_dict

# Cell

import alphapept.recalibration


def recalibrate_data(
    settings,
    logger_set=False,
    settings_parsed=False,
    callback=None
):
    if not logger_set:
        set_logger()
    if not settings_parsed:
        settings = check_version_and_hardware(settings)
    if settings['search']['calibrate']:
        logging.info('Performing recalibration.')

        if not callback:
            cb = functools.partial(tqdm_wrapper, tqdm.tqdm(total=1))
        else:
            cb = callback

        offsets = alphapept.recalibration.calibrate_hdf_parallel(
            settings,
            callback=cb
        )

        logging.info('Recalibration complete.')
    return settings

# Cell

import alphapept.score


def score(
    settings,
    pept_dict=None,
    fasta_dict=None,
    logger_set=False,
    settings_parsed=False,
    callback=None
):
    if not logger_set:
        set_logger()
    if not settings_parsed:
        settings = check_version_and_hardware(settings)
    if not callback:
        cb = functools.partial(tqdm_wrapper, tqdm.tqdm(total=1))
    else:
        cb = callback

    if (fasta_dict is None) or (pept_dict is None):
        db_data = alphapept.fasta.read_database(
            settings['fasta']['database_path']
        )
        fasta_dict = db_data['fasta_dict'].item()
        pept_dict = db_data['pept_dict'].item()
    alphapept.score.score_hdf_parallel(settings, callback=cb)
    logging.info('Scoring complete.')

    if not settings['fasta']['save_db']:
        pept_dict = alphapept.fasta.pept_dict_from_search(settings)

    # Protein groups
    logging.info('Extracting protein groups.')

    if not callback:
        cb = functools.partial(tqdm_wrapper, tqdm.tqdm(total=1))
    else:
        cb = callback

    # This is on each file individually -> when having repeats maybe
    # use differently (if this matter at all )
    alphapept.score.protein_groups_hdf_parallel(
        settings,
        pept_dict,
        fasta_dict,
        callback=cb
    )
    logging.info('Protein groups complete.')

    return settings

# Cell

import alphapept.matching
import pandas as pd


def align(
    settings,
    logger_set=False,
    settings_parsed=False,
    callback=None
):
    if not logger_set:
        set_logger()
    if not settings_parsed:
        settings = check_version_and_hardware(settings)

    alphapept.matching.align_datasets(settings)

    return settings

def match(
    settings,
    logger_set=False,
    settings_parsed=False,
    callback=None
):
    if not logger_set:
        set_logger()
    if not settings_parsed:
        settings = check_version_and_hardware(settings)

    if settings['matching']['match_between_runs']:
        alphapept.matching.match_datasets(settings)

    return settings

# Cell

import alphapept.quantification
import pandas as pd


def lfq_quantification(
    settings,
    logger_set=False,
    settings_parsed=False,
    callback=None
):
    if not logger_set:
        set_logger()
    if not settings_parsed:
        settings = check_version_and_hardware(settings)
    field = settings['quantification']['mode']

    logging.info('Assembling dataframe.')
    df = alphapept.utils.assemble_df(settings)
    logging.info('Assembly complete.')

    if field in df.keys():  # Check if the quantification information exists.
        # We could include another protein fdr in here..
        if 'fraction' in df.keys():
            logging.info('Delayed Normalization.')
            df, normalization = alphapept.quantification.delayed_normalization(
                df,
                field
            )
            pd.DataFrame(normalization).to_hdf(
                settings['experiment']['results_path'],
                'fraction_normalization'
            )
            df_grouped = df.groupby(
                ['shortname', 'precursor', 'protein', 'filename']
            )[['{}_dn'.format(field)]].sum().reset_index()
        else:
            df_grouped = df.groupby(
                ['shortname', 'precursor', 'protein', 'filename']
            )[field].sum().reset_index()

        df.to_hdf(
            settings['experiment']['results_path'],
            'combined_protein_fdr_dn'
        )

        logging.info('Complete. ')
        logging.info('Starting profile extraction.')

        if not callback:
            cb = functools.partial(tqdm_wrapper, tqdm.tqdm(total=1))
        else:
            cb = callback

        protein_table = alphapept.quantification.protein_profile_parallel(
            settings,
            df_grouped,
            callback=cb
        )
        protein_table.to_hdf(
            settings['experiment']['results_path'],
            'protein_table'
        )
        results_path = settings['experiment']['results_path']
        base, ext = os.path.splitext(results_path)
        protein_table.to_csv(base+'.csv')

        logging.info('LFQ complete.')
    return settings

# Cell

import yaml


def export(
    settings,
    logger_set=False,
    settings_parsed=False,
    callback=None
):
    if not logger_set:
        set_logger()
    if not settings_parsed:
        settings = check_version_and_hardware(settings)
    base, ext = os.path.splitext(settings['experiment']['results_path'])
    out_path_settings = base+'.yaml'

    with open(out_path_settings, 'w') as file:
        yaml.dump(settings, file)

    logging.info('Settings saved to {}'.format(out_path_settings))
    logging.info('Analysis complete.')
    return settings

# Cell

def run_complete_workflow(
    settings,
    logger_set=False,
    settings_parsed=False,
    callback=None
):
    if not logger_set:
        set_logger()
    if not settings_parsed:
        settings = check_version_and_hardware(settings)
    settings = create_database(
        settings,
        logger_set=True,
        settings_parsed=True,
    )
    settings = import_raw_data(
        settings,
        logger_set=True,
        settings_parsed=True,
    )
    settings = feature_finding(
        settings,
        logger_set=True,
        settings_parsed=True,
    )
    settings, pept_dict, fasta_dict = search_data(
        settings,
        logger_set=True,
        settings_parsed=True,
    )
    settings = recalibrate_data(
        settings,
        logger_set=True,
        settings_parsed=True,
    )
    settings, pept_dict, fasta_dict = search_data(
        settings,
        recalibrated=True,
        logger_set=True,
        settings_parsed=True,
    )
    settings = score(
        settings,
        pept_dict=pept_dict,
        fasta_dict=fasta_dict,
        logger_set=True,
        settings_parsed=True,
    )
    settings = align(
        settings,
        logger_set=True,
        settings_parsed=True,
    )
    settings = match(
        settings,
        logger_set=True,
        settings_parsed=True,
    )
    settings = lfq_quantification(
        settings,
        logger_set=True,
        settings_parsed=True,
    )
    settings = export(
        settings,
        logger_set=True,
        settings_parsed=True,
    )

    return settings

# Cell

import click
import os
import alphapept.settings
from .__version__ import VERSION_NO
from .__version__ import COPYRIGHT
from .__version__ import URL

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
CLICK_SETTINGS_OPTION = click.argument(
    "settings_file",
#     help="A .yaml file with settings.",
    type=click.Path(exists=True, dir_okay=False),
#     default=f"{os.path.dirname(__file__)}/settings_template.yaml"
)


def run_cli():
    print(
        "\n".join(
            [
                "\n",
                r"     ___    __      __          ____             __ ",
                r"    /   |  / /___  / /_  ____  / __ \___  ____  / /_",
                r"   / /| | / / __ \/ __ \/ __ \/ /_/ / _ \/ __ \/ __/",
                r"  / ___ |/ / /_/ / / / / /_/ / ____/ ___/ /_/ / /_  ",
                r" /_/  |_/_/ .___/_/ /_/\__,_/_/    \___/ .___/\__/  ",
                r"         /_/                          /_/           ",
                '.'*52,
                '.{}.'.format(URL.center(50)),
                '.{}.'.format(COPYRIGHT.center(50)),
                '.{}.'.format(VERSION_NO.center(50)),
                '.'*52,
                "\n"
            ]
        )
    )
    cli_overview.add_command(cli_database)
    cli_overview.add_command(cli_import)
    cli_overview.add_command(cli_feature_finding)
    cli_overview.add_command(cli_search)
    cli_overview.add_command(cli_recalibrate)
    cli_overview.add_command(cli_score)
    cli_overview.add_command(cli_quantify)
    cli_overview.add_command(cli_export)
    cli_overview.add_command(cli_workflow)
    cli_overview.add_command(cli_gui)
    cli_overview()


@click.group(
    context_settings=CONTEXT_SETTINGS,
#     help="AlphaPept"
)
def cli_overview():
    pass


@click.command(
    "database",
    help="Create a database from a fasta file.",
    short_help="Create a database from a fasta file."
)
@CLICK_SETTINGS_OPTION
def cli_database(settings_file):
    settings = alphapept.settings.load_settings(settings_file)
    create_database(settings)


@click.command(
    "import",
    help="Import and convert raw data from vendor to `.ms_data.hdf` file.",
    short_help="Import and convert raw data from vendor to `.ms_data.hdf` file."
)
@CLICK_SETTINGS_OPTION
def cli_import(settings_file):
    settings = alphapept.settings.load_settings(settings_file)
    import_raw_data(settings)


@click.command(
    "features",
    help="Find features in a `.ms_data.hdf` file.",
    short_help="Find features in a `.ms_data.hdf` file."
)
@CLICK_SETTINGS_OPTION
def cli_feature_finding(settings_file):
    settings = alphapept.settings.load_settings(settings_file)
    feature_finding(settings)


@click.command(
    "search",
    help="Search and identify feature in a `.ms_data.hdf` file.",
    short_help="Search and identify feature in a `.ms_data.hdf` file."
)
@CLICK_SETTINGS_OPTION
@click.option(
    '--recalibrated_features',
    '-r',
    'recalibrated',
    help="Use recalibrated features if present",
    is_flag=True,
    default=False,
    show_default=True,
)
def cli_search(settings_file, recalibrated):
    settings = alphapept.settings.load_settings(settings_file)
    search_data(settings, recalibrated)


@click.command(
    "recalibrate",
    help="Recalibrate a `.ms_data.hdf` file.",
    short_help="Recalibrate a `.ms_data.hdf` file."
)
@CLICK_SETTINGS_OPTION
def cli_recalibrate(settings_file):
    settings = alphapept.settings.load_settings(settings_file)
    recalibrate_data(settings)


@click.command(
    "score",
    help="Score PSM from a `.ms_data.hdf` file.",
    short_help="Score PSM from a `.ms_data.hdf` file."
)
@CLICK_SETTINGS_OPTION
def cli_score(settings_file):
    settings = alphapept.settings.load_settings(settings_file)
    score(settings)

@click.command(
    "align",
    help="Align multiple `.ms_data.hdf` files.",
    short_help="Align multiple `.ms_data.hdf` files."
)
@CLICK_SETTINGS_OPTION
def cli_align(settings_file):
    settings = alphapept.settings.load_settings(settings_file)
    align(settings)

@click.command(
    "match",
    help="Perform match between run type analysis on multiple `.ms_data.hdf` files.",
    short_help="Perform match between run type analysis on multiple `.ms_data.hdf` files."
)
@CLICK_SETTINGS_OPTION
def cli_match(settings_file):
    settings = alphapept.settings.load_settings(settings_file)
    align(settings)
    match(settings)

@click.command(
    "quantify",
    help="Quantify and compare multiple `.ms_data.hdf` files.",
    short_help="Quantify and compare multiple `.ms_data.hdf` files."
)
@CLICK_SETTINGS_OPTION
def cli_quantify(settings_file):
    settings = alphapept.settings.load_settings(settings_file)
    lfq_quantification(settings)


@click.command(
    "export",
    help="Export protein table from `.ms_data.hdf` files as `.csv`",
    short_help="Export protein table from `.ms_data.hdf` files as `.csv`."
)
@CLICK_SETTINGS_OPTION
def cli_export(settings_file):
    settings = alphapept.settings.load_settings(settings_file)
    export(settings)


@click.command(
    "workflow",
    help="Run the complete AlphaPept workflow.",
    short_help="Run the complete AlphaPept workflow."
)
@CLICK_SETTINGS_OPTION
def cli_workflow(settings_file):
    settings = alphapept.settings.load_settings(settings_file)
    run_complete_workflow(settings)


@click.command(
    "gui",
    help="Start graphical user interface for AlphaPept.",
)
@click.option(
    "--test",
    "test",
    help="Test",
    is_flag=True,
    default=False,
    show_default=True,
)
def cli_gui(test):
    print('Launching GUI')
    import alphapept.ui
    if test:
        alphapept.ui.main(close=True)
    else:
        alphapept.ui.main()
