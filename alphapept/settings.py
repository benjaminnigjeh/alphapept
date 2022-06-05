# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/00_settings.ipynb (unless otherwise specified).

__all__ = ['print_settings', 'load_settings', 'load_settings_as_template', 'save_settings', 'SETTINGS_TEMPLATE',
           'workflow', 'general', 'experiment', 'raw', 'fasta', 'modfile_path', 'mod_db', 'mods', 'mods_terminal',
           'mods_protein', 'proteases', 'features', 'search', 'score', 'calibration', 'matching', 'quantification',
           'hash_file', 'create_default_settings', 'HOME', 'AP_PATH', 'DEFAULT_SETTINGS_PATH', 'skip', 'previous_md5']

# Cell
import yaml
import os

def print_settings(settings: dict):
    """Print a yaml settings file

    Args:
        settings (dict): A yaml dictionary.
    """
    print(yaml.dump(settings, default_flow_style=False))


def load_settings(path: str):
    """Load a yaml settings file.

    Args:
        path (str): Path to the settings file.
    """
    with open(path, "r") as settings_file:
        SETTINGS_LOADED = yaml.load(settings_file, Loader=yaml.FullLoader)
        return SETTINGS_LOADED


def load_settings_as_template(path: str):
    """Loads settings but removes fields that contain summary information.

    Args:
        path (str): Path to the settings file.
    """
    settings = load_settings(path)

    for _ in ['summary','failed']:
        if _ in settings:
            settings.pop(_)

    _ = 'prec_tol_calibrated'
    if 'search' in settings:
        if _ in settings['search']:
            settings['search'].pop(_)

    return settings


def save_settings(settings: dict, path: str):
    """Save settings file to path.

    Args:
        settings (dict): A yaml dictionary.
        path (str): Path to the settings file.
    """

    base_dir = os.path.dirname(path)

    if base_dir != '':
        os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w") as file:
        yaml.dump(settings, file, sort_keys=False)

# Cell
import pandas as pd
from .constants import protease_dict

SETTINGS_TEMPLATE = {}

# Workflow
workflow = {}

workflow["continue_runs"] = {'type':'checkbox', 'default':False, 'description':"Flag to continue previously computated runs. If False existing ms_data will be deleted."}
workflow["create_database"] = {'type':'checkbox', 'default':True, 'description':"Flag to create a database."}
workflow["import_raw_data"] = {'type':'checkbox', 'default':True, 'description':"Flag to import the raw data."}
workflow["find_features"] = {'type':'checkbox', 'default':True, 'description':"Flag to perform feature finding."}
workflow["search_data"] = {'type':'checkbox', 'default':True, 'description':"Flag to perform search."}
workflow["recalibrate_data"] = {'type':'checkbox', 'default':True, 'description':"Flag to perform recalibration."}
workflow["align"] = {'type':'checkbox', 'default':False, 'description':"Flag to align the data."}
workflow["match"] = {'type':'checkbox', 'default':False, 'description':"Flag to perform match-between runs."}
workflow["lfq_quantification"] = {'type':'checkbox', 'default':True, 'description':"Flag to perfrom lfq normalization."}

SETTINGS_TEMPLATE["workflow"] = workflow

# Cell
general = {}

general['n_processes'] = {'type':'spinbox', 'min':1, 'max':60, 'default':60, 'description':"Maximum number of processes for multiprocessing. If larger than number of processors it will be capped."}

SETTINGS_TEMPLATE["general"] = general

# Cell
experiment = {}

experiment["results_path"] = {'type':'path','default': None, 'filetype':['hdf'], 'folder':False, 'description':"Path where the results should be stored."}
experiment["shortnames"] = {'type':'list','default':[], 'description':"List of shortnames for the raw files."}
experiment["file_paths"] = {'type':'list','default':[], 'description':"Filepaths of the experiments."}
experiment["sample_group"] = {'type':'list','default':[], 'description':"Sample group, for raw files that should be quanted together."}
experiment["matching_group"] = {'type':'list','default':[], 'description':"List of macthing groups for the raw files. This only allows match-between-runs of files within the same groups."}
experiment["fraction"] = {'type':'list','default':[], 'description':"List of fraction numbers for fractionated samples."}
experiment["database_path"] = {'type':'path','default':None, 'filetype':['hdf'], 'folder':False, 'description':"Path to library file (.hdf)."}
experiment["fasta_paths"] = {'type':'list','default':[], 'description':"List of paths for FASTA files."}

SETTINGS_TEMPLATE["experiment"] = experiment

# Cell
raw = {}

raw["n_most_abundant"] = {'type':'spinbox', 'min':1, 'max':1000, 'default':400, 'description':"Number of most abundant peaks to be isolated from raw spectra."}
raw["use_profile_ms1"] = {'type':'checkbox', 'default':False, 'description':"Use profile data for MS1 and perform own centroiding."}

SETTINGS_TEMPLATE["raw"] = raw

# Cell
import os
fasta = {}

## Read modifications from modifications file

try:
    base = os.path.dirname(os.path.abspath(__file__)) #Cant do this in notebook
except NameError:
    base = os.path.join(os.pardir, 'alphapept')

modfile_path = os.path.join(base, "modifications.tsv")

mod_db = pd.read_csv(modfile_path, sep='\t')

mods = {}
mods_terminal = {}
mods_protein = {}

for i in range(len(mod_db)):
    mod = mod_db.iloc[i]
    if 'terminus' in mod['Type']:
        if 'peptide' in mod['Type']:
            mods_terminal[mod['Identifier']] = mod['Description']
        elif 'protein' in mod['Type']:
            mods_protein[mod['Identifier']] = mod['Description']
        else:
            print('Not understood')
            print(mod['Type'])
    else:
        mods[mod['Identifier']] = mod['Description']

fasta["mods_fixed"] = {'type':'checkgroup', 'value':mods.copy(), 'default':['cC'],'description':"Fixed modifications."}
fasta["mods_fixed_terminal"] = {'type':'checkgroup', 'value':mods_terminal.copy(), 'default':[],'description':"Fixed terminal modifications."}
fasta["mods_variable"] = {'type':'checkgroup', 'value':mods.copy(), 'default':['oxM'],'description':"Variable modifications."}
fasta["mods_variable_terminal"]  = {'type':'checkgroup', 'value':mods_terminal.copy(), 'default':[], 'description':"Varibale terminal modifications."}

fasta["mods_fixed_terminal_prot"] = {'type':'checkgroup', 'value':mods_protein.copy(), 'default':[],'description':"Fixed terminal modifications on proteins."}
fasta["mods_variable_terminal_prot"]  = {'type':'checkgroup', 'value':mods_protein.copy(), 'default':['a<^'], 'description':"Varibale terminal modifications on proteins."}

fasta["n_missed_cleavages"] = {'type':'spinbox', 'min':0, 'max':99, 'default':2, 'description':"Number of missed cleavages."}
fasta["pep_length_min"] = {'type':'spinbox', 'min':7, 'max':99, 'default':7, 'description':"Minimum peptide length."}
fasta["pep_length_max"] = {'type':'spinbox', 'min':7, 'max':99, 'default':27, 'description':"Maximum peptide length."}
fasta["isoforms_max"] = {'type':'spinbox', 'min':1, 'max':4096, 'default':1024, 'description':"Maximum number of isoforms per peptide."}
fasta["n_modifications_max"] = {'type':'spinbox', 'min':1, 'max':10, 'default':3, 'description':"Limit the number of modifications per peptide."}

fasta["pseudo_reverse"] = {'type':'checkbox', 'default':True, 'description':"Use pseudo-reverse strategy instead of reverse."}
fasta["AL_swap"] = {'type':'checkbox', 'default':False, 'description':"Swap A and L for decoy generation."}
fasta["KR_swap"] = {'type':'checkbox', 'default':False, 'description':"Swap K and R (only if terminal) for decoy generation."}

proteases = [_ for _ in protease_dict.keys()]
fasta["protease"] = {'type':'combobox', 'value':proteases, 'default':'trypsin', 'description':"Protease for digestions."}

fasta["spectra_block"] = {'type':'spinbox', 'min':1000, 'max':1000000, 'default':100000, 'description':"Maximum number of sequences to be collected before theoretical spectra are generated."}
fasta["fasta_block"] = {'type':'spinbox', 'min':100, 'max':10000, 'default':1000, 'description':"Number of fasta entries to be processed in one block."}
fasta["save_db"] = {'type':'checkbox', 'default':True, 'description':"Save DB or create on the fly."}
fasta["fasta_size_max"] = {'type':'spinbox', 'min':1, 'max':1000000, 'default':100, 'description':"Maximum size of FASTA (MB) when switching on-the-fly."}

SETTINGS_TEMPLATE["fasta"] = fasta

# Cell

features = {}
# Thermo FF settings

features["max_gap"] = {'type':'spinbox', 'min':1, 'max':10, 'default':2}
features["centroid_tol"] = {'type':'spinbox', 'min':1, 'max':25, 'default':8}
features["hill_length_min"] = {'type':'spinbox', 'min':1, 'max':10, 'default':3}
features["hill_split_level"] = {'type':'doublespinbox', 'min':0.1, 'max':10.0, 'default':1.3}
features["iso_split_level"] = {'type':'doublespinbox', 'min':0.1, 'max':10.0, 'default':1.3}

features["hill_smoothing"] = {'type':'spinbox', 'min':1, 'max':10, 'default':1}
features["hill_check_large"] = {'type':'spinbox', 'min':1, 'max':100, 'default':40}

features["iso_charge_min"] = {'type':'spinbox', 'min':1, 'max':6, 'default':1}
features["iso_charge_max"] = {'type':'spinbox', 'min':1, 'max':6, 'default':6}
features["iso_n_seeds"] = {'type':'spinbox', 'min':1, 'max':500, 'default':100}

features["hill_nboot_max"] = {'type':'spinbox', 'min':1, 'max':500, 'default':300}
features["hill_nboot"] = {'type':'spinbox', 'min':1, 'max':500, 'default':150}

features["iso_mass_range"] = {'type':'spinbox', 'min':1, 'max':10, 'default':5}
features["iso_corr_min"] = {'type':'doublespinbox', 'min':0.1, 'max':1, 'default':0.6}

features["map_mz_range"] = {'type':'doublespinbox', 'min':0.1, 'max':2, 'default':1.5}
features["map_rt_range"] = {'type':'doublespinbox', 'min':0.1, 'max':1, 'default':0.5}
features["map_mob_range"] = {'type':'doublespinbox', 'min':0.1, 'max':1, 'default':0.3}
features["map_n_neighbors"] = {'type':'spinbox', 'min':1, 'max':10, 'default':5}

features["search_unidentified"] = {'type':'checkbox', 'default':False, 'description':"Search MSMS w/o feature."}

SETTINGS_TEMPLATE["features"] = features

# Cell
# Search Settings
search = {}

search["prec_tol"] = {'type':'spinbox', 'min':1, 'max':500, 'default':30, 'description':"Maximum allowed precursor mass offset."}
search["frag_tol"] = {'type':'spinbox', 'min':1, 'max':500, 'default':30, 'description':"Maximum fragment mass tolerance."}
search["min_frag_hits"] = {'type':'spinbox', 'min':1, 'max':99, 'default':7, 'description':"Minimum number of fragment hits."}
search["ppm"] = {'type':'checkbox', 'default':True, 'description':"Use ppm instead of Dalton."}
search["calibrate"] = {'type':'checkbox', 'default':True, 'description':"Recalibrate masses."}
search["calibration_std_prec"] = {'type':'spinbox', 'min':1, 'max':10, 'default':5, 'description':"Std range for precursor tolerance after calibration."}
search["calibration_std_frag"] = {'type':'spinbox', 'min':1, 'max':10, 'default':5, 'description':"Std range for fragment tolerance after calibration."}
search["parallel"] = {'type':'checkbox', 'default':True, 'description':"Use parallel processing."}
search["peptide_fdr"] = {'type':'doublespinbox', 'min':0.0, 'max':1.0, 'default':0.01, 'description':"FDR level for peptides."}
search["protein_fdr"] = {'type':'doublespinbox', 'min':0.0, 'max':1.0, 'default':0.01, 'description':"FDR level for proteins."}
search['recalibration_min'] = {'type':'spinbox', 'min':100, 'max':10000, 'default':100, 'description':"Minimum number of datapoints to perform calibration."}

SETTINGS_TEMPLATE["search"] = search

# Cell
# Score
score = {}

score["method"] = {'type':'combobox', 'value':['x_tandem','random_forest'], 'default':'random_forest', 'description':"Scoring method."}
SETTINGS_TEMPLATE["score"] = score

# Cell
# Calibration
calibration = {}

calibration["outlier_std"] = {'type':'spinbox', 'min':1, 'max':5, 'default':3, 'description':"Number of std. deviations to filter outliers in psms."}
calibration["calib_n_neighbors"] = {'type':'spinbox', 'min':1, 'max':1000, 'default':100, 'description':"Number of neighbors that are used for offset interpolation."}
calibration["calib_mz_range"] = {'type':'spinbox', 'min':1, 'max':1000, 'default':20, 'description':"Scaling factor for mz axis."}
calibration["calib_rt_range"] = {'type':'doublespinbox', 'min':0.0, 'max':10, 'default':0.5, 'description':"Scaling factor for rt axis."}
calibration["calib_mob_range"] = {'type':'doublespinbox', 'min':0.0, 'max':1.0, 'default':0.3, 'description':"Scaling factor for mobility axis."}

SETTINGS_TEMPLATE["calibration"] = calibration

# Cell
# Matching

matching = {}

matching["match_p_min"] = {'type':'doublespinbox', 'min':0.001, 'max':1.0, 'default':0.05, 'description':"Minimum probability cutoff for matching."}
matching["match_d_min"] = {'type':'doublespinbox', 'min':0.001, 'max':10.0, 'default':3, 'description': "Minimum distance cutoff for matching."}
matching["match_group_tol"] = {'type':'spinbox', 'min':0, 'max':100, 'default':0, 'description': "When having matching groups, match neighboring groups."}


SETTINGS_TEMPLATE["matching"] = matching

# Cell
# Quantification

quantification = {}
quantification["max_lfq"] = {'type':'checkbox', 'default':True, 'description':"Perform max lfq type quantification."}
quantification["lfq_ratio_min"] = {'type':'spinbox', 'min':1, 'max':10, 'default':1, 'description':"Minimum number of ratios for LFQ."}
quantification["mode"] = {'type':'combobox', 'value':['ms1_int_sum_apex'], 'default':'ms1_int_sum_apex', 'description':"Column to perform quantification on."}

SETTINGS_TEMPLATE["quantification"] = quantification

# Cell
import sys
import hashlib

def hash_file(path):
    """
    Helper function to hash a file
    Taken from https://stackoverflow.com/questions/22058048/hashing-a-file-in-python
    """

    BUF_SIZE = 65536  # lets read stuff in 64kb chunks!

    md5 = hashlib.md5()
    sha1 = hashlib.sha1()

    with open(path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)
            sha1.update(data)

    return md5.hexdigest(), sha1.hexdigest()


# Cell

def create_default_settings():

    settings = {}

    for category in SETTINGS_TEMPLATE.keys():

        temp_settings = {}

        for key in SETTINGS_TEMPLATE[category].keys():
            temp_settings[key] = SETTINGS_TEMPLATE[category][key]['default']

        settings[category] = temp_settings

    md5, sha1 = hash_file(modfile_path)
    settings['general']['modfile_hash'] = md5

    save_settings(settings, DEFAULT_SETTINGS_PATH) #Save in home folder to be able to modify
    save_settings(SETTINGS_TEMPLATE,  os.path.join(AP_PATH, 'settings_template.yaml'))


import os
import logging

md5, sha1 = hash_file(modfile_path)

HOME = os.path.expanduser("~")
AP_PATH = os.path.join(HOME, ".alphapept")
DEFAULT_SETTINGS_PATH = os.path.join(AP_PATH, 'default_settings.yaml')

skip = False

previous_md5 = None
if os.path.isfile(DEFAULT_SETTINGS_PATH):
    s_ = load_settings(DEFAULT_SETTINGS_PATH)
    if 'modfile_hash' in s_['general']:
        previous_md5 = s_['general']['modfile_hash']

if previous_md5 is not None:
    if previous_md5 == md5:
        skip = True

if not skip:
    logging.info('Creating default settings.')
    create_default_settings()
else:
    logging.info('Using existing settings.')