# AUTOGENERATED! DO NOT EDIT! File to edit: nbs\11_settings.ipynb (unless otherwise specified).

__all__ = ['print_settings', 'settings', 'raw', 'fasta', 'search', 'features', 'general', 'calibration']

# Cell
settings = {}

raw = {}
raw["most_abundant"] = 400
raw["raw_path"] = ''
raw["raw_path_npz"] = ''
raw["raw_folder"] = ''

fasta = {}

fasta["protease"] = "trypsin"
fasta["num_missed_cleavages"] = 2
fasta["min_length"] = 6
fasta["max_length"] = 27
fasta["mods_variable"] = ["oxM"]
fasta["mods_variable_terminal"] = []
fasta["mods_fixed"] = ["cC"]
fasta["mods_fixed_terminal"] = []
fasta["mods_fixed_terminal_prot"] = []
fasta["mods_variable_terminal_prot"]  = []
fasta["max_isoforms"] = 1024
fasta["fasta_path"] = ""
fasta["library_path"] = ""
fasta["fasta_folder"] = ""

search = {}

search["m_offset"] = 20
search["m_tol"] = 20
search["min_frag_hits"] = 7
search["ppm"] = True
search["parallel"] = True
search["calibrate"] = True
search["calibration_std"] = 3
search["peptide_fdr"] = 0.01
search["protein_fdr"] = 0.01

features = {}

features["min_hill_length"] = 3
features["max_gap"] = 2
features["ppm_tol"] = 8
features["smoothing"] = 1

features["max_neighbors"] = 4
features["max_distance"] = 0.2
features["mass_importance"] = 100

general = {}

general["settings_path"] = ""
general["parallel"] = True
general["ppm"] = True
general["create_library"] = True
general["convert_raw"] = True

calibration = {}

calibration["min_mz_step"] = 80
calibration["min_rt_step"] = 50
calibration["minimum_score"] = 20
calibration["outlier_std"] = 3
calibration["method"] = 'linear'

settings['raw'] = raw
settings['fasta'] = fasta
settings['search'] = search
settings['features'] = features
settings['general'] = general
settings['calibration']  = calibration

def print_settings(settings):
    """
    Print settings
    """
    import yaml
    print(yaml.dump(settings, default_flow_style=False))