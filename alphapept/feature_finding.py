# AUTOGENERATED! DO NOT EDIT! File to edit: nbs\04_feature_finding.ipynb (unless otherwise specified).

__all__ = ['get_peaks', 'get_centroid', 'gaussian_estimator', 'raw_to_centroid', 'get_pairs_centroids', 'tup_to_ind',
           'ind_to_tup', 'connect_centroids_forward', 'connect_centroids_backward', 'connect_centroids', 'get_hills',
           'plot_hill', 'smooth_mean', 'smooth_median', 'smooth', 'get_minima', 'split_hills', 'split_hill',
           'split_recursive', 'filter_hills', 'weighted_average', 'get_hill_stats', 'get_hill_data_numba',
           'get_hill_data', 'check_isotope_pattern', 'DELTA_M', 'DELTA_S', 'cosinec', 'extract_edge', 'get_edges',
           'plot_pattern', 'check_isotope_pattern_directed', 'grow', 'grow_trail', 'get_trails',
           'isolate_isotope_pattern', 'check_averagine', 'pattern_to_mz', 'cosine_averagine', 'int_list_to_array',
           'mz_to_mass', 'get_minpos', 'get_local_minima', 'is_local_minima', 'truncate', 'M_PROTON',
           'get_isotope_patterns', 'feature_finder_report', 'plot_isotope_pattern', 'find_features']

# Cell
from numba import njit
import numpy as np

@njit
def get_peaks(int_array):
    "Detects peaks in an array."

    peaklist = []
    gradient = np.diff(int_array)
    start, center, end = -1, -1, -1

    for i in range(len(gradient)):

        grad = gradient[i]

        if (end == -1) & (center == -1):  # No end and no center yet
            if grad <= 0:  # If decreasing, move start point
                start = i
            else:  # If increasing set as center point
                center = i

        if (end == -1) & (
            center != -1
        ):  # If we have a centerpoint and it is still increasing set as new center
            if grad >= 0:
                center = i
            else:  # If it is decreasing set as endpoint
                end = i

        if end != -1:  # If we have and endpoint and it is going down
            if grad < 0:
                end = i  # Set new Endpoint
            else:  # if it stays the same or goes up set a new peak
                peaklist.append((start + 1, center + 1, end + 1))
                start, center, end = end, -1, -1  # Reset start, center, end

    if end != -1:
        peaklist.append((start + 1, center + 1, end + 1))

    return peaklist

# Cell
from numba import njit

@njit
def get_centroid(peak, mz_array, int_array):
    """
    Wrapper to estimate centroid center positions
    """
    start, center, end = peak
    mz_int = np.sum(int_array[start + 1 : end])

    peak_size = end - start - 1

    if peak_size == 1:
        mz_cent = mz_array[center]
    elif peak_size == 2:
        mz_cent = (
            mz_array[start + 1] * int_array[start + 1]
            + mz_array[end - 1] * int_array[end - 1]
        ) / (int_array[start + 1] + int_array[end - 1])
    else:
        mz_cent = gaussian_estimator(peak, mz_array, int_array)

    return mz_cent, mz_int

@njit
def gaussian_estimator(peak, mz_array, int_array):
    """
    Three-point gaussian estimator.
    """
    start, center, end = peak

    m1, m2, m3 = mz_array[center - 1], mz_array[center], mz_array[center + 1]
    i1, i2, i3 = int_array[center - 1], int_array[center], int_array[center + 1]

    if i1 == 0:  # Case of sharp flanks
        m = (m2 * i2 + m3 * i3) / (i2 + i3)
    elif i3 == 0:
        m = (m1 * i1 + m2 * i2) / (i1 + i2)
    else:
        l1, l2, l3 = np.log(i1), np.log(i2), np.log(i3)
        m = (
            ((l2 - l3) * (m1 ** 2) + (l3 - l1) * (m2 ** 2) + (l1 - l2) * (m3 ** 2))
            / ((l2 - l3) * (m1) + (l3 - l1) * (m2) + (l1 - l2) * (m3))
            * 1
            / 2
        )

    return m

# Cell
from numba.typed import List

def raw_to_centroid(query_data, callback=None):

    scans = query_data['scan_list_ms1']
    rts = query_data['rt_list_ms1']
    masses = query_data['mass_list_ms1']
    intensities = query_data['int_list_ms1']

    centroid_dtype = [("mz", float), ("int", np.int64), ("scan_no", int), ("rt", float)]
    centroids_pre = []


    for i in range(len(masses)):
        scan_no = scans[i]
        rt = rts[i]
        mass_arr = masses[i]
        ints_arr = intensities[i]

        centroids_pre.append(
            [(mz, intensity, scan_no, rt) for mz, intensity in zip(mass_arr, ints_arr)]
        )

        if callback:
            callback((i+1)/len(masses)/2)

    centroids = []

    for i, _ in enumerate(centroids_pre):
        centroids.append(np.array(_, dtype=centroid_dtype))
        if callback:
            callback((len(masses)+i+1)/len(masses)/2)

    return centroids

# Cell
@njit
def get_pairs_centroids(centroids_1, centroids_2, ppm_tol=8):
    """
    Function to compare two centroid list and extract pairs.
    """
    pairs = List()
    i, j = 0, 0
    while (i < len(centroids_1)) & (j < len(centroids_2)):
        mz1, mz2 = centroids_1[i]["mz"], centroids_2[j]["mz"]

        diff = mz1 - mz2

        mz_sum = mz1 + mz2

        delta = 2 * 1e6 * np.abs(diff) / mz_sum

        if delta < ppm_tol:
            pairs.append((i, j, delta))
            i += 1
        elif diff > 0:
            j += 1
        else:
            i += 1

    return pairs

# Cell
from numba import int32, float32

@njit
def tup_to_ind(tup, r_shape):
    """
    Convert tuple to index
    """
    ind = r_shape[1] * tup[0] + tup[1]
    return ind

@njit
def ind_to_tup(ind, r_shape):
    """
    Convert index to tuple
    """
    row = ind // r_shape[1]
    col = ind - row * r_shape[1]
    return (row, col)

@njit
def connect_centroids_forward(centroids, max_centroids, max_gap, ppm_tol):
    """
    Function to connect lists of centroids - forward direction
    """

    connections = (
        np.zeros(
            (len(centroids), max_centroids, max_gap+1), dtype=int32
        )
        - 1
    )

    scores = (
        np.zeros(
            (len(centroids), max_centroids, max_gap+1), dtype=float32
        )
        + np.inf
    )


    c_shape = connections.shape

    for gap in range(max_gap+1):
        j = 1 + gap

        for i in range(len(centroids) - gap - 1):
            centroids_1 = centroids[i]
            centroids_2 = centroids[i + j]

            for pair in get_pairs_centroids(centroids_1, centroids_2, ppm_tol):
                ii = pair[0]
                jj = pair[1]
                delta = pair[2]
                index = tup_to_ind((i + j, jj), c_shape)

                if scores[i, ii, gap] > delta:
                    connections[i, ii, gap] = index
                    scores[i, ii, gap] = delta

    return connections, scores


@njit
def connect_centroids_backward(centroids, max_centroids, max_gap, ppm_tol):
    """
    Function to connect lists of centroids - backward direction
    """

    connections = (
        np.zeros(
            (len(centroids), max_centroids, max_gap+1), dtype=int32
        )
        - 1
    )

    scores = (
        np.zeros(
            (len(centroids), max_centroids, max_gap+1), dtype=float32
        )
        + np.inf
    )


    c_shape = connections.shape

    for gap in range(max_gap+1):
        j = 1 + gap

        for i in range(len(centroids) - gap - 1):
            centroids_2 = centroids[i]
            centroids_1 = centroids[i + j]

            for pair in get_pairs_centroids(centroids_1, centroids_2, ppm_tol):
                jj = pair[0]
                ii = pair[1]
                delta = pair[2]
                index = tup_to_ind((i + j, jj), c_shape)

                if scores[i, ii, gap] > delta:
                    connections[i, ii, gap] = index
                    scores[i, ii, gap] = delta

    return connections, scores


def connect_centroids(centroids, max_gap = 2 , ppm_tol = 8):
    """
    Wrapper function to connect lists of centroids via foward and backward search
    """
    max_centroids = np.max([len(_) for _ in centroids])

    connections_f, scores_f = connect_centroids_forward(centroids, max_centroids, max_gap, ppm_tol)
    connections_b, scores_b = connect_centroids_backward(centroids, max_centroids, max_gap, ppm_tol)

    connections = (
        np.zeros(
            (len(centroids), max_centroids, max_gap+1), dtype=np.int
        )
        - 1
    )

    connections[connections_f == connections_b] = connections_f[connections_f == connections_b]

    c_shape = connections.shape

    from_r, from_c, from_g = np.where(connections >= 0)
    to_r, to_c = ind_to_tup(connections[from_r, from_c, from_g], c_shape)

    return from_r, from_c, to_r, to_c

# Cell
import networkx as nx
from collections import Counter

def get_hills(centroids, max_gap = 2, min_hill_length = 3, ppm_tol = 8, buffer_size = 2000, callback=None):

    """
    Function to get hills from connected centroids

    """

    from_r, from_c, to_r, to_c = connect_centroids(centroids, max_gap, ppm_tol)

    completed_hills = []
    current_scan = 0

    idx = 0

    G = nx.Graph()

    for current_scan in range(0, len(centroids)):
        #Feed edges until next scan
        while from_r[idx] == current_scan:
            G.add_edge((from_r[idx], from_c[idx]), (to_r[idx], to_c[idx]))
            if idx < len(from_r)-1:
                idx+=1
            else:
                break


        if current_scan % buffer_size == 0:
            # Get all connected components:
            c_comps = list(nx.connected_components(G))

            for hill in c_comps:
                if len(hill) >= min_hill_length:
                    hill = list(hill)
                    hill.sort()
                    max_scan = hill[-1][0]

                    if max_scan < current_scan - max_gap: #can't be more
                        completed_hills.append(hill)

                        for node in hill:
                            G.remove_node(node)

        if callback:
            callback((current_scan+1)/len(centroids))


    c_comps = list(nx.connected_components(G))
    for hill in c_comps:
        if len(hill) >= min_hill_length:
            hill = list(hill)
            hill.sort()
            completed_hills.append(hill)

    return completed_hills

# Cell
import matplotlib.pyplot as plt
plt.style.use('ggplot')

def plot_hill(hill, centroids):

    """
    Helper function to plot the hill
    """

    hill_data = np.array([centroids[_[0]][_[1]] for _ in hill])

    f, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10,10))
    ax1.plot(hill_data["rt"], hill_data["int"])
    ax1.set_title('Hill')
    ax1.set_xlabel('RT (min)')
    ax1.set_ylabel('Intensity')

    ax2.plot(hill_data["rt"], hill_data["mz"])
    ax2.set_xlabel('RT (min)')
    ax2.set_ylabel('m/z')

# Cell
@njit
def smooth_mean(y, window):
    "Mean smoothing"
    y_new = np.zeros(len(y))
    for i in range(len(y)):
        min_index = np.max(np.array([0, i - window]))
        max_index = np.min(np.array([len(y), i + window + 1]))
        y_new[i] = np.mean(y[min_index:max_index])

    return y_new

@njit
def smooth_median(y, window):
    "Median smoothing"
    y_new = np.zeros(len(y))
    for i in range(len(y)):
        min_index = np.max(np.array([0, i - window]))
        max_index = np.min(np.array([len(y), i + window + 1]))
        y_new[i] = np.median(y[min_index:max_index])

    return y_new

@njit
def smooth(y, window):
    "First median smoothing, then mean smoothing"

    y = smooth_median(y, window)
    y = smooth_mean(y, window)

    return y

# Cell
@njit
def get_minima(y):
    """
    Function extract the mimnima of a trace.
    Here, the definition of a minimum is:
    (1) left and right value are larger
    (2) second right and left are larger, right is equal
    (3) second left and right are larger, left is equal

    """
    minima = []
    for i in range(2, len(y) - 2):
        if (y[i - 1] > y[i]) & (y[i + 1] > y[i]):
            minima.append(i)
        elif (y[i - 1] > y[i]) & (y[i + 1] == y[i]) & (y[i + 2] > y[i]):
            minima.append(i)
        elif (y[i - 2] > y[i]) & (y[i - 1] == y[i]) & (y[i + 1] > y[i]):
            minima.append(i)
        elif (
            (y[i - 2] > y[i])
            & (y[i - 1] == y[i])
            & (y[i + 1] == y[i])
            & (y[i + 2] > y[i])
        ):
            minima.append(i)
    return minima

# Cell
def split_hills(hills, centroids, smoothing = 1, split_level=1.3, callback=None):
    """
    Wrapper to split list of hills
    """
    split_hills = []
    for index, current_hill in enumerate(hills):
        hill_data = np.array([centroids[_[0]][_[1]] for _ in current_hill])

        split_hills.extend(split_hill(hill_data, current_hill, smoothing, split_level))

        if callback:
            callback((index+1)/len(hills))

    split_hills.sort(key=len, reverse=True)

    return split_hills

def split_hill(hill_data, current_hill, smoothing, split_level):
    """
    Wrapper to call recursive function to split hill
    """
    y = hill_data["int"]
    y_smooth = smooth(y, smoothing)

    splits = split_recursive(current_hill, y_smooth, split_level)

    return splits



def split_recursive(current_hill, y_smooth, split_level):
    """
    Recursive function to split hill
    """

    splits = []

    minima = np.array(get_minima(y_smooth), dtype=np.int64)
    sorted_minima = minima[np.argsort(y_smooth[minima])]

    for minpos in sorted_minima:  # Loop through minima, start with lowest value

        minval = y_smooth[minpos]

        left_side = y_smooth[:minpos]
        right_side = y_smooth[minpos:]

        left_hill = current_hill[:minpos]
        right_hill = current_hill[minpos:]

        left_max = np.max(left_side)
        right_max = np.max(right_side)

        minimum_max = np.min(np.array((left_max, right_max)))

        if minval == 0:
            minval = np.finfo(float).eps
        if minimum_max / minval > split_level:
            splits_left = split_recursive(left_hill, left_side, split_level)
            splits_right = split_recursive(right_hill, right_side, split_level)

            splits.extend(splits_left)
            splits.extend(splits_right)

            return splits

    return [current_hill]

# Cell
def filter_hills(hills, centroids, hill_min_length=2, hill_peak_factor=2, hill_peak_min_length=40, smoothing=1, callback=None):
    """
    Wrapper function to perform filtering on lists of hills
    """
    filtered_hills = []
    for idx, current_hill in enumerate(hills):
        if len(current_hill) > hill_min_length:
            if len(current_hill) < hill_peak_min_length:
                filtered_hills.append(current_hill)
            else:
                hill_data = np.array([centroids[_[0]][_[1]] for _ in current_hill])
                int_profile = hill_data["int"]
                maximum = np.max(int_profile)
                y_smooth = smooth(int_profile, smoothing)

                if (maximum / y_smooth[0] > hill_peak_factor) & (maximum / y_smooth[-1] > hill_peak_factor):
                    filtered_hills.append(current_hill)

        if callback:
            callback((idx+1) / len(hills))

    return filtered_hills

# Cell
@njit
def weighted_average(array, weights):
    """
    Calculate the weighted average of an array
    """
    return np.sum((array * weights)) / np.sum(weights)

# Cell

@njit
def get_hill_stats(hill_data, hill_nboot = 150, hill_nboot_max = 300):

    """
    Calculate hill statistics with bootstraping and weighted averages
    """

    min_rt, max_rt = hill_data["rt"].min(), hill_data["rt"].max()
    summed_intensity = hill_data["int"].sum()
    apex_intensity = hill_data["int"].max()

    if len(hill_data) > hill_nboot_max:
        bootsize = hill_nboot_max
    else:
        bootsize = len(hill_data)

    averages = np.zeros(hill_nboot)

    average = 0

    for i in range(hill_nboot):
        boot = hill_data[np.random.choice(len(hill_data), bootsize, replace=True)]
        boot_mz = weighted_average(boot["mz"], boot["int"])
        averages[i] = boot_mz
        average += boot_mz

    average_mz = average/hill_nboot

    delta = 0
    for i in range(hill_nboot):
        delta += (average_mz - averages[i]) ** 2 #maybe easier?

    delta_m = np.sqrt(delta / (hill_nboot - 1))

    return average_mz, delta_m, min_rt, max_rt, summed_intensity, apex_intensity


@njit
def get_hill_data_numba(hill_data):
    hill_stats = np.zeros((len(hill_data), 6))
    for i in range(len(hill_data)):
        average_mz, delta_m, min_rt, max_rt, summed_intensity, apex_intensity = get_hill_stats(hill_data[i])
        hill_stats[i, 0] = average_mz
        hill_stats[i, 1] = delta_m
        hill_stats[i, 2] = min_rt
        hill_stats[i, 3] = max_rt
        hill_stats[i, 4] = summed_intensity
        hill_stats[i, 5] = apex_intensity

    return hill_stats


def get_hill_data(hills, centroids, callback=None):
    """
    Function to calculate hill statistics from hills
    """

    centroid_dtype = [("mz", float), ("int", np.int64), ("scan_no", int), ("rt", float)]

    hill_data = []

    for idx, hill in enumerate(hills):
        hill_data.append(np.array([centroids[_[0]][_[1]] for _ in hill], dtype=centroid_dtype))

        if callback:
            callback((idx+1)/len(hills)*0.5) #First half


    hill_stats = get_hill_data_numba(hill_data)

    stats_dtype = [
            ("mz_avg", float),
            ("delta_m", float),
            ("rt_min", float),
            ("rt_max", float),
            ("int_sum", "int64"),
            ("int_max", int),
        ]

    sortindex = np.argsort(hill_stats[:, 2])
    sorted_stats = hill_stats[sortindex]
    sorted_hills = np.array(hills)[sortindex]
    sorted_data = np.array(hill_data)[sortindex]

    sorted_stats = np.core.records.fromarrays(sorted_stats.T, dtype=stats_dtype)

    sorted_data_numba = List()

    for idx, _ in enumerate(sorted_data):
        sorted_data_numba.append(_)

        if callback:
            callback((idx+1)/len(sorted_data)+0.5) #Second half

    return sorted_hills, sorted_stats, sorted_data_numba

# Cell
from .constants import mass_dict
from numba import njit

DELTA_M = mass_dict['delta_M']
DELTA_S = mass_dict['delta_S']

@njit
def check_isotope_pattern(mass1, mass2, delta_mass1, delta_mass2, charge, mass_range = 5):
    """
    Check if two masses could belong to the same isotope pattern
    """
    delta_mass1 = delta_mass1 * mass_range
    delta_mass2 = delta_mass2 * mass_range

    delta_mass = np.abs(mass1 - mass2)

    left_side = np.abs(delta_mass - DELTA_M / charge)
    right_side = np.sqrt((DELTA_S / charge) ** 2 + delta_mass1 ** 2 + delta_mass2 ** 2)

    return left_side <= right_side

# Cell
@njit
def cosinec(hill_data_one, hill_data_two):
    """
    Cosine Correlation of two hills
    """
    int_one = hill_data_one["int"]
    spec_one = hill_data_one["scan_no"]

    int_two = hill_data_two["int"]
    spec_two = hill_data_two["scan_no"]

    min_one, max_one = spec_one[0], spec_one[-1]
    min_two, max_two = spec_two[0], spec_two[-1]

    if min_one + 3 > max_two:  # at least an overlap of 3 elements
        corr = 0
    elif min_two + 3 > max_one:
        corr = 0
    else:
        min_s = np.min(np.array([min_one, min_two]))
        max_s = np.max(np.array([max_one, max_two]))

        int_one_scaled = np.zeros(int(max_s - min_s + 1))
        int_two_scaled = np.zeros(int(max_s - min_s + 1))

        int_one_scaled[spec_one - min_s] = int_one
        int_two_scaled[spec_two - min_s] = int_two

        corr = np.sum(int_one_scaled * int_two_scaled) / np.sqrt(
            np.sum(int_one_scaled ** 2) * np.sum(int_two_scaled ** 2)
        )

    return corr

# Cell
@njit
def extract_edge(sorted_stats, runner, maxindex, min_charge = 1, max_charge = 6, mass_range=5):
    """
    Extract edge
    """

    maximum_offset = DELTA_M + DELTA_S

    edges = []

    mass1, delta_mass1, rt_min, rt_max = (
        sorted_stats[runner]["mz_avg"],
        sorted_stats[runner]["delta_m"],
        sorted_stats[runner]["rt_min"],
        sorted_stats[runner]["rt_max"],
    )

    delta = 1

    for index in range(runner + 1, maxindex):

        mass2, delta_mass2, rt_min = (
            sorted_stats[index]["mz_avg"],
            sorted_stats[index]["delta_m"],
            sorted_stats[index]["rt_min"],
        )

        if np.abs(mass2 - mass1) <= maximum_offset:
            for charge in range(min_charge, max_charge + 1):
                if check_isotope_pattern(mass1, mass2, delta_mass1, delta_mass2, charge, mass_range):
                    edges.append((runner, index))
                    break

    return edges

import networkx as nx

def get_edges(sorted_stats, hill_datas, cc_cutoff = 0.6, min_charge=1, max_charge=6, mass_range=5, callback=None, **kwargs):
    """
    Wrapper function to extract pre isotope patterns
    """

    pre_isotope_patterns = []

    idxs_upper = sorted_stats["rt_min"].searchsorted(
        sorted_stats["rt_max"], side="right"
    )

    pre_edges = []
    delta = []

    # Step 1
    for runner in range(len(sorted_stats)):
        pre_edges.extend(extract_edge(sorted_stats, runner, idxs_upper[runner], min_charge, max_charge, mass_range))

        if callback:
            callback((runner+1)/len(sorted_stats)*1/2)

    # Step 2
    edges = []
    for runner in range(len(pre_edges)):
        edge = pre_edges[runner]

        x = edge[0]
        y = edge[1]

        if cosinec(hill_datas[x], hill_datas[y]) > cc_cutoff:
            edges.append(edge)

        if callback:
            callback((runner+1)/len(pre_edges)*1/2+1/2)


    # Step 3
    G2 = nx.Graph()
    for edge in edges:
        G2.add_edge(edge[0], edge[1])

    pre_isotope_patterns = [
        sorted(list(c))
        for c in sorted(nx.connected_components(G2), key=len, reverse=True)
    ]

    return pre_isotope_patterns

# Cell

def plot_pattern(pattern, sorted_hills, centroids, hill_data):

    """
    Helper function to plot a pattern
    """
    f, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10,10))

    mzs = []
    rts = []
    ints = []
    for entry in pattern:
        hill = sorted_hills[entry]
        hill_data = np.array([centroids[_[0]][_[1]] for _ in hill])

        int_profile = hill_data["int"]
        ax1.plot(hill_data["rt"], hill_data["int"])
        ax2.scatter(hill_data["rt"], hill_data["mz"], s = hill_data["int"]/5e5 )


    ax1.set_title('Pattern')
    ax1.set_xlabel('RT (min)')
    ax1.set_ylabel('Intensity')

    ax2.set_xlabel('RT (min)')
    ax2.set_ylabel('m/z')

    plt.show()

# Cell

@njit
def check_isotope_pattern_directed(mass1, mass2, delta_mass1, delta_mass2, charge, index, mass_range):
    """
    Check if two masses could belong to the same isotope pattern

    """
    delta_mass1 = delta_mass1 * mass_range
    delta_mass2 = delta_mass2 * mass_range

    left_side = np.abs(mass1 - mass2 - index * DELTA_M / charge)
    right_side = np.sqrt((DELTA_S / charge) ** 2 + delta_mass1 ** 2 + delta_mass2 ** 2)

    return left_side <= right_side


@njit
def grow(trail, seed, direction, relative_pos, index, stats, data, pattern, charge, mass_range):
    """
    Grows isotope pattern based on a seed and direction

    """
    x = pattern[seed]  # This is the seed

    mass1 = stats[x]["mz_avg"]
    delta_mass1 = stats[x]["delta_m"]
    hill_data_one = data[x]

    growing = True

    while growing:
        if direction == 1:
            if seed + relative_pos == len(pattern):
                growing = False
                break
        else:
            if seed + relative_pos < 0:
                growing = False
                break

        y = pattern[seed + relative_pos]  # This is a reference peak
        hill_data_two = data[y]
        mass2 = stats[y]["mz_avg"]
        delta_mass2 = stats[y]["delta_m"]


        if cosinec(hill_data_one, hill_data_two) > 0.6:
            if check_isotope_pattern_directed(mass1, mass2, delta_mass1, delta_mass2, charge, -direction * index, mass_range):
                if direction == 1:
                    trail.append(y)
                else:
                    trail.insert(0, y)
                index += (
                    1
                )  # Greedy matching: Only one edge for a specific distance, will not affect the following matches

        delta_mass = np.abs(mass1 - mass2)

        if (delta_mass > (DELTA_M+DELTA_S) * index):  # the pattern is sorted so there is a maximum to look back
            break

        relative_pos += direction

    return trail

@njit
def grow_trail(seed, pattern, stats, data, charge, mass_range):
    """
    Wrapper to grow an isotope pattern to the left and right side
    """
    x = pattern[seed]
    trail = List()
    trail.append(x)
    trail = grow(trail, seed, -1, -1, 1, stats, data, pattern, charge, mass_range)
    trail = grow(trail, seed, 1, 1, 1, stats, data, pattern, charge, mass_range)

    return trail


@njit
def get_trails(seed, pattern, stats, data, mass_range, charge_range):
    """
    Wrapper to extract trails for a given charge range
    """
    trails = []
    for charge in charge_range:
        trail = grow_trail(seed, pattern, stats, data, charge, mass_range)
        trails.append(trail)

    return trails

# Cell
from .constants import averagine_aa, isotopes, mass_dict
from .chem import mass_to_dist

from numba import int64
@njit
def isolate_isotope_pattern(pre_pattern, stats, data, mass_range, charge_range, averagine_aa, isotopes, seed_masses):
    """
    Isolate isotope patterns
    """
    longest_trace = 0
    champion_trace = None
    champion_charge = 0

    # Sort patterns by mass
    sortindex = np.argsort(stats[pre_pattern]["mz_avg"])  # [::-1]
    sorted_pattern = pre_pattern[sortindex]
    massindex = np.argsort(stats[sorted_pattern]["int_sum"])[::-1][:seed_masses]

    # Use all the elements in the pre_pattern as seed

    for seed in massindex:  # Loop through all seeds
        seed_global = sorted_pattern[seed]

        trails = get_trails(seed, sorted_pattern, stats, data, mass_range, charge_range)


        for index, trail in enumerate(trails):
            if len(trail) > longest_trace:  # Needs to be longer than the current champion

                #print(type(trail))

                arr = int_list_to_array(trail)

                intensity_profile = stats[arr]["int_sum"]

                seedpos = np.nonzero(arr==seed_global)[0][0]

                # truncate around the seed...
                arr = truncate(arr, intensity_profile, seedpos)

                # Remove lower masses:
                # Take the index of the maximum and remove all masses on the left side
                if charge_range[index] * stats[seed_global]["mz_avg"] < 1000:
                    maxpos = np.argmax(intensity_profile)
                    arr = arr[maxpos:]

                if len(arr) > longest_trace:
                    # Averagine check
                    cc = check_averagine(stats, arr, charge_range[index], averagine_aa, isotopes)
                    if cc > 0.6:
                        # Update the champion
                        champion_trace = arr
                        champion_charge = charge_range[index]
                        longest_trace = len(arr)


    return champion_trace, champion_charge

@njit
def check_averagine(stats, pattern, charge, averagine_aa, isotopes):

    masses, intensity = pattern_to_mz(stats, pattern, charge)

    spec_one = np.floor(masses).astype(int64)
    int_one = intensity

    spec_two, int_two = mass_to_dist(np.min(masses), averagine_aa, isotopes) # maybe change to no rounded version

    spec_two = np.floor(spec_two).astype(int64)

    return cosine_averagine(int_one, int_two, spec_one, spec_two)

@njit
def pattern_to_mz(stats, pattern, charge):
    """
    Function to calculate masses and intensities from pattern for a given charge
    """
    mzs = np.zeros(len(pattern))
    ints = np.zeros(len(pattern))

    for i in range(len(pattern)):
        entry = pattern[i]
        mzs[i] = mz_to_mass(stats[entry]["mz_avg"], charge)
        ints[i] = stats[entry]["int_sum"]

    sortindex = np.argsort(mzs)

    masses = mzs[sortindex]
    intensity = ints[sortindex]

    return masses, intensity

@njit
def cosine_averagine(int_one, int_two, spec_one, spec_two):

    min_one, max_one = spec_one[0], spec_one[-1]
    min_two, max_two = spec_two[0], spec_two[-1]

    min_s = np.min(np.array([min_one, min_two]))
    max_s = np.max(np.array([max_one, max_two]))

    int_one_scaled = np.zeros(int(max_s - min_s + 1))
    int_two_scaled = np.zeros(int(max_s - min_s + 1))

    int_one_scaled[spec_one - min_s] = int_one
    int_two_scaled[spec_two - min_s] = int_two

    corr = np.sum(int_one_scaled * int_two_scaled) / np.sqrt(
        np.sum(int_one_scaled ** 2) * np.sum(int_two_scaled ** 2)
    )

    return corr

@njit
def int_list_to_array(numba_list):
    """
    Numba compatbilte function to convert a numba list with integers to a numpy array
    """
    array = np.zeros(len(numba_list), dtype=np.int64)

    for i in range(len(array)):

        array[i] = numba_list[i]

    return array

M_PROTON = mass_dict['Proton']

@njit
def mz_to_mass(mz, charge):
    """
    Function to calculate the mass from a mz value.
    """
    if charge < 0:
        raise NotImplementedError("Negative Charges not implemented.")

    mass = mz * charge - charge * M_PROTON

    return mass


@njit
def get_minpos(y, split=1.3):
    """
    Function to get a list of minima in a trace.
    A minimum is returned if the ratio of lower of the surrounding maxima to the minimum is larger than the splitting factor.
    """
    minima = get_local_minima(y)
    minima_list = List()

    for minpos in minima:

        minval = y[minpos]
        left_side = y[:minpos]
        right_side = y[minpos:]

        left_max = np.max(left_side)
        right_max = np.max(right_side)

        minimum_max = np.min(np.array((left_max, right_max)))

        if minimum_max / minval > split:
            minima_list.append(minpos)

    return minima_list

@njit
def get_local_minima(y):
    """
    Function to return all local minima of a array
    """
    minima = List()
    for i in range(1, len(y) - 1):
        if is_local_minima(y, i):
            minima.append(i)
    return minima


@njit
def is_local_minima(y, i):
    return (y[i - 1] > y[i]) & (y[i + 1] > y[i])


#export
@njit
def truncate(array, intensity_profile, seedpos):
    """
    Function to truncate an intensity profile around its seedposition
    """
    minima = int_list_to_array(get_minpos(intensity_profile))

    if len(minima) > 0:
        left_minima = minima[minima < seedpos]
        right_minima = minima[minima > seedpos]

        # If the minimum is smaller than the seed
        if len(left_minima) > 0:
            minpos = left_minima[-1]
        else:
            minpos = 0

        if len(right_minima) > 0:
            maxpos = right_minima[0]
        else:
            maxpos = len(array)

        array = array[minpos:maxpos+1]

    return array

# Cell
def get_isotope_patterns(pre_isotope_patterns, stats, data, averagine_aa, isotopes, min_charge = 1, max_charge = 6, mass_range = 5, seed_masses = 100, callback=None):
    """
    Wrapper function to iterate over pre_isotope_patterns
    """

    isotope_patterns = []
    isotope_charges = []

    charge_range = List()

    for i in range(min_charge, max_charge + 1):
        charge_range.append(i)

    isotope_patterns = []
    isotope_charges = []

    for idx, pre_pattern in enumerate(pre_isotope_patterns):
        extract = True
        while extract:
            isotope_pattern, isotope_charge = isolate_isotope_pattern(np.array(pre_pattern), stats, data, mass_range, charge_range, averagine_aa, isotopes, seed_masses)
            if isotope_pattern is None:
                length = 0
            else:
                length = len(isotope_pattern)

            if length > 1:
                isotope_charges.append(isotope_charge)
                isotope_patterns.append(isotope_pattern)

                pre_pattern = [_ for _ in pre_pattern if _ not in isotope_pattern]

                if len(pre_pattern) <= 1:
                    extract = False
            else:
                extract = False


        if callback:
            callback((idx+1)/len(pre_isotope_patterns))


    return isotope_patterns, isotope_charges

# Cell

#ToDo: include callback
from .feature_finding import mz_to_mass

import pandas as pd
def feature_finder_report(isotope_patterns, isotope_charges, sorted_stats, sorted_data, sorted_hills, query_data, callback=None):
    """
    Write a summary table

    """

    rt_list_ms1 = query_data['rt_list_ms1']
    scan_list_ms1 = query_data['scan_list_ms1']

    scan_no_dict = {_: rt_list_ms1[i] for i, _ in enumerate(scan_list_ms1)} #lookup table for retention time based on scan-index
    rt_dict = {_: i for i, _ in enumerate(rt_list_ms1)} #lookup table for retention time based on scan-index

    data = []

    for runner in range(len(isotope_patterns)):

        isotope_data = np.hstack([sorted_data[_] for _ in isotope_patterns[runner]])

        mz = np.min(isotope_data['mz'])

        mz_std = np.std(sorted_stats[isotope_patterns[runner]]['delta_m'])

        charge = isotope_charges[runner]

        mass = mz_to_mass(mz, charge)

        maxint = np.argmax(isotope_data['int'])

        most_abundant_mz = isotope_data['mz'][maxint]

        rt_start = isotope_data['rt'].min()
        rt_end = isotope_data['rt'].max()


        # Approximate apex and rt_apex

        argmax = np.argmax(isotope_data['int'])

        int_apex = isotope_data['int'][argmax]


        rt_apex = isotope_data['rt'][argmax]

        smoothed_profile = smooth(isotope_data['int'], 1)

        argmax_smooth = np.argmax(isotope_data['int'])

        half_max = smoothed_profile.max()/2
        nearest_left = np.abs(smoothed_profile[:argmax_smooth+1]-half_max).argmin()
        nearest_right = np.abs(smoothed_profile[argmax_smooth:]-half_max).argmin() + argmax

        fwhm = isotope_data['rt'][nearest_right] - isotope_data['rt'][nearest_left]

        # FWHM

        n_isotopes = len(isotope_patterns[runner])

        n_scans = np.max([len(_) for _ in sorted_hills[isotope_patterns[runner]]])

        int_sum = np.sum(isotope_data['int'])
        data.append((mz, mz_std, most_abundant_mz, charge, rt_start, rt_apex, rt_end, fwhm, n_isotopes, n_scans, mass, int_apex, int_sum))

        if callback:
            callback((runner+1)/len(isotope_patterns))


    df = pd.DataFrame(data, columns = ['mz', 'mz_std', 'most_abundant_mz', 'charge', 'rt_start', 'rt_apex', 'rt_end', 'fwhm',
           'n_isotopes', 'n_scans', 'mass', 'int_apex','int_sum'])

    df.sort_values(['rt_start','mz'])

    return df

# Cell
def plot_isotope_pattern(index, df, sorted_stats, centroids, scan_range=100, mz_range=2, plot_hills = False):
    """
    Plot an isotope pattern in its local environment
    """

    markersize = 10
    plot_offset_mz = 1
    plot_offset_rt = 2

    feature =  df.loc[index]

    scan = rt_dict[feature['rt_apex']]

    start_scan = scan-scan_range
    end_scan = scan+scan_range

    mz_min = feature['mz']-mz_range-plot_offset_mz
    mz_max = feature['mz']+mz_range+plot_offset_mz

    sub_data = np.hstack(centroids[start_scan:end_scan])

    selection = sub_data[(sub_data['mz']>mz_min) & (sub_data['mz']<mz_max)]

    min_rt = selection['rt'].min() - plot_offset_rt
    max_rt = selection['rt'].max() + plot_offset_rt

    hill_selection = sorted_stats[(sorted_stats['mz_avg']>mz_min) & (sorted_stats['mz_avg']<mz_max) & (sorted_stats['rt_max']<max_rt) & (sorted_stats['rt_min']>min_rt)]

    plt.style.use('dark_background')

    plt.figure(figsize=(15,15))
    plt.scatter(selection['rt'], selection['mz'], c= np.log(selection['int']), marker='s', s=markersize, alpha=0.9)
    plt.colorbar()
    plt.grid(False)
    plt.xlabel('RT (min)')
    plt.ylabel('m/z')

    box_height = mz_range/50

    if plot_hills:
        for hill in hill_selection:
            bbox = [hill['rt_min'], hill['mz_avg']-box_height, hill['rt_max'], hill['mz_avg']+box_height]

            rect = plt.Rectangle((bbox[0], bbox[1]),
                                      bbox[2] - bbox[0],
                                      bbox[3] - bbox[1], fill=False,
                                      edgecolor='w', linewidth=1, alpha = 0.3)
            plt.gca().add_patch(rect)


    feature_selection = df[(df['mz']>mz_min) & (df['mz']<mz_max) & (df['rt_end']<max_rt) & (df['rt_start']>min_rt)]

    for f_idx in feature_selection.index:
        for c_idx in range(len(sorted_stats[isotope_patterns[f_idx]])-1):

            start = sorted_stats[isotope_patterns[f_idx]][c_idx]
            end = sorted_stats[isotope_patterns[f_idx]][c_idx+1]

            start_mass = start['mz_avg']
            start_rt = (start['rt_min']+start['rt_max'])/2

            end_mass = end['mz_avg']
            end_rt = (end['rt_min']+end['rt_max'])/2

            plt.plot([start_rt, end_rt], [start_mass, end_mass], '+', color='y')
            plt.plot([start_rt, end_rt], [start_mass, end_mass], ':', color='y')

        if plot_hills:
            for hill_idx in isotope_patterns[f_idx]:

                hill = sorted_stats[hill_idx]
                bbox = [hill['rt_min'], hill['mz_avg']-box_height, hill['rt_max'], hill['mz_avg']+box_height]

                rect = plt.Rectangle((bbox[0], bbox[1]),
                                          bbox[2] - bbox[0],
                                          bbox[3] - bbox[1], fill=False,
                                          edgecolor='g', linewidth=1, alpha = 0.8)
                plt.gca().add_patch(rect)


    plt.xlim([min_rt+plot_offset_rt, max_rt-plot_offset_rt])
    plt.ylim([mz_min+plot_offset_mz, mz_max-plot_offset_mz])
    plt.title('Pattern')
    plt.show()

    plt.style.use('ggplot')

# Cell
from time import time
def find_features(query_data, callback = None, **kwargs):
    """
    Wrapper for feature finding
    """

    start = time()
    centroids = raw_to_centroid(query_data)

    print('Loaded {:,} centroids.'.format(len(centroids)))

    completed_hills = get_hills(centroids)

    print('A total of {:,} hills extracted. Average hill length {:.2f}'.format(len(completed_hills), np.mean([len(_) for _ in completed_hills])))

    splitted_hills = split_hills(completed_hills, centroids, smoothing=1)

    print('Split {:,} hills into {:,} hills'.format(len(completed_hills), len(splitted_hills)))

    filtered_hills = filter_hills(splitted_hills, centroids)

    print('Filtered {:,} hills. Remaining {:,} hills'.format(len(splitted_hills), len(filtered_hills)))

    sorted_hills, sorted_stats, sorted_data = get_hill_data(filtered_hills, centroids)

    print('Extracting hill stats complete')

    pre_isotope_patterns = get_edges(sorted_stats, sorted_data)

    print('Found {} pre isotope patterns.'.format(len(pre_isotope_patterns)))

    isotope_patterns, isotope_charges = get_isotope_patterns(pre_isotope_patterns, sorted_stats, sorted_data, averagine_aa, isotopes)

    print('Extracted {} isotope patterns.'.format(len(isotope_patterns)))

    df = feature_finder_report(isotope_patterns, isotope_charges, sorted_stats, sorted_data, sorted_hills, query_data)

    print('Report complete.')

    end = time()

    print('Time elapsed {}'. format(end-start))

    return df