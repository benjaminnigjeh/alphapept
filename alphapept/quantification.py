# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/08_quantification.ipynb (unless otherwise specified).

__all__ = ['gaussian', 'return_elution_profile', 'simulate_sample_profiles', 'get_peptide_error',
           'get_total_error_parallel', 'get_total_error', 'normalize_experiment_SLSQP', 'delayed_normalization',
           'minimum_occurence']

# Cell
import random
import numpy as np

def gaussian(mu, sigma, grid):
    norm = 0.3989422804014327 / sigma
    return norm * np.exp(-0.5 * ((grid - mu) / sigma) ** 2)


def return_elution_profile(timepoint, sigma, n_runs):
    """
    Simulation of a Gaussian Elution Profile
    """
    return gaussian(timepoint, sigma, np.arange(0, n_runs))


def simulate_sample_profiles(n_peptides, n_runs, n_samples, threshold=0.2, use_noise=True):
    """
    Generate random profiles to serve as test data

    """
    abundances = np.random.rand(n_peptides)*10e7
    true_normalization = np.random.normal(loc=1, scale=0.1, size=(n_runs, n_samples))

    true_normalization[true_normalization<0] = 0

    true_normalization = true_normalization/np.max(true_normalization)

    maxvals = np.max(true_normalization, axis=1)

    elution_timepoints = random.choices(list(range(n_runs)), k=n_peptides)

    profiles = np.empty((n_runs, n_samples, n_peptides))
    profiles[:] = np.nan

    for i in range(n_peptides):

        elution_timepoint = elution_timepoints[i]
        abundance = abundances[i]

        profile = return_elution_profile(elution_timepoint, 1, n_runs)
        profile = profile/np.max(profile)
        profile = profile * abundance
        elution_profiles = np.tile(profile, (n_samples, 1)).T

        # Some gaussian noise
        if use_noise:
            noise = np.random.normal(1, 0.2, elution_profiles.shape)
            noisy_profile = noise * elution_profiles
        else:
            noisy_profile = elution_profiles

        #print(noisy_profile)

        normalized_profile = noisy_profile * true_normalization

        normalized_profile[normalized_profile < threshold] = 0
        normalized_profile[normalized_profile == 0] = np.nan


        profiles[:,:,i] = normalized_profile

    return profiles, true_normalization

# Cell
from numba import njit, prange

@njit
def get_peptide_error(profile, normalization):

    pep_ints = np.zeros(profile.shape[1])

    normalized_profile = profile*normalization

    for i in range(len(pep_ints)):
        pep_ints[i] = np.nansum(normalized_profile[:,i])

    pep_ints = pep_ints[pep_ints>0]

    # Loop through all combinations
    n = len(pep_ints)

    error = 0
    for i in range(n):
        for j in range(i+1,n):
            error += np.abs(np.log(pep_ints[i]/pep_ints[j]))**2

    return error


@njit(parallel=True)
def get_total_error_parallel(normalization, profiles):

    normalization = normalization.reshape(profiles.shape[:2])

    total_error = 0

    for index in prange(profiles.shape[2]):
        total_error += get_peptide_error(profiles[:,:, index], normalization)

    return total_error


def get_total_error(normalization, profiles):

    normalization = normalization.reshape(profiles.shape[:2])

    total_error = 0

    for index in range(profiles.shape[2]):
        total_error += get_peptide_error(profiles[:,:, index], normalization)

    return total_error

# Cell
from scipy.optimize import minimize
import pandas as pd
import numpy as np

minimum_occurence = 10

def normalize_experiment_SLSQP(profiles):
    """
    Calculate normalization with SLSQP approach
    """
    x0 = np.ones(profiles.shape[0] * profiles.shape[1])
    bounds = [(0.1, 1) for _ in x0]
    res = minimize(get_total_error, args = profiles , x0 = x0, bounds=bounds, method='SLSQP', options={'disp': False} )

    solution = res.x/np.max(res.x)
    solution = solution.reshape(profiles.shape[:2])

    return solution

def delayed_normalization(df, field='int_sum', minimum_occurence=None):
    """
    Returns normalization for given peptide intensities
    """
    experiments = np.sort(df['experiment'].unique()).tolist()
    fractions = np.sort(df['fraction'].unique()).tolist()

    n_fractions = len(fractions)
    n_experiments = len(experiments)

    df_max = df.groupby(['precursor','fraction','experiment'])[field].max() #Maximum per fraction

    prec_count = df_max.index.get_level_values('precursor').value_counts()

    if not minimum_occurence:
        minimum_occurence = np.percentile(prec_count[prec_count>1], 75) #Take the 25% best datapoints

    shared_precs = prec_count[prec_count >= minimum_occurence]
    precs = prec_count[prec_count > minimum_occurence].index.tolist()

    n_profiles = len(precs)

    selected_precs = df_max.loc[precs]
    selected_precs = selected_precs.reset_index()

    profiles = np.empty((n_fractions, n_experiments, n_profiles))
    profiles[:] = np.nan

    #get dictionaries
    fraction_dict = {_:i for i,_ in enumerate(fractions)}
    experiment_dict = {_:i for i,_ in enumerate(experiments)}
    precursor_dict = {_:i for i,_ in enumerate(precs)}

    prec_id = [precursor_dict[_] for _ in selected_precs['precursor']]
    frac_id = [fraction_dict[_] for _ in selected_precs['fraction']]
    ex_id = [experiment_dict[_] for _ in selected_precs['experiment']]

    profiles[frac_id,ex_id, prec_id] = selected_precs[field]

    normalization = normalize_experiment_SLSQP(profiles)

    df[field+'_dn'] = df[field]*normalization[[fraction_dict[_] for _ in df['fraction']], [experiment_dict[_] for _ in df['experiment']]]

    return df, normalization