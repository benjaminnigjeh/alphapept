# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/10_constants.ipynb (unless otherwise specified).

__all__ = ['AAs', 'get_mass_dict', 'modfile_path', 'aafile_path', 'mass_dict', 'Isotope', 'spec', 'isotopes',
           'averagine_aa', 'averagine_avg', 'protease_dict', 'loss_dict', 'LABEL', 'label_dict']

# Cell
AAs = set('ACDEFGHIKLMNPQRSTUVWY')

# Cell

from numba import types
from numba.typed import Dict
import os

#generates the mass dictionary from table
def get_mass_dict(modfile:str, aasfile: str, verbose:bool=True):
    """
    Function to create a mass dict based on tsv files.
    This is used to create the hardcoded dict in the constants notebook.
    The dict needs to be hardcoded because of importing restrictions when using numba.
    More specifically, a global needs to be typed at runtime.

    Args:
        modfile (str): Filename of modifications file.
        aasfile (str): Filename of AAs file.
        verbose (bool, optional): Flag to print dict.

    Returns:
        Returns a numba compatible dictionary with masses.

    Raises:
        FileNotFoundError: If files are not found.

    """
    import pandas as pd

    mods = pd.read_csv(modfile, delimiter="\t")
    aas = pd.read_csv(aasfile, delimiter="\t")

    mass_dict = Dict.empty(key_type=types.unicode_type, value_type=types.float64)

    for identifier, mass in aas[["Identifier", "Monoisotopic Mass (Da)"]].values:
        mass_dict[identifier] = float(mass)

    for identifier, aar, mass in mods[
        ["Identifier", "Amino Acid Residue", "Monoisotopic Mass Shift (Da)"]
    ].values:
        #print(identifier, aar, mass)

        if ("<" in identifier) or (">" in identifier):
            for aa_identifier, aa_mass in aas[["Identifier", "Monoisotopic Mass (Da)"]].values:
                if '^' in identifier:
                    new_identifier = identifier[:-2] + aa_identifier
                    mass_dict[new_identifier] = float(mass) + mass_dict[aa_identifier]
                elif aar == aa_identifier:
                    new_identifier = identifier[:-2] + aa_identifier
                    mass_dict[new_identifier] = float(mass) + mass_dict[aa_identifier]
                else:
                    pass
        else:
            mass_dict[identifier] = float(mass) + mass_dict[aar]

    # Manually add other masses
    mass_dict[
        "Electron"
    ] = (
        0.000548579909070
    )  # electron mass, half a millimass error if not taken into account
    mass_dict["Proton"] = 1.00727646687  # proton mass
    mass_dict["Hydrogen"] = 1.00782503223  # hydrogen mass
    mass_dict["C13"] = 13.003354835  # C13 mass
    mass_dict["Oxygen"] = 15.994914619  # oxygen mass
    mass_dict["OH"] = mass_dict["Oxygen"] + mass_dict["Hydrogen"]  # OH mass
    mass_dict["H2O"] = mass_dict["Oxygen"] + 2 * mass_dict["Hydrogen"]  # H2O mass

    mass_dict["NH3"] = 17.03052
    mass_dict["delta_M"] = 1.00286864
    mass_dict["delta_S"] = 0.0109135

    if verbose:

        for element in mass_dict:
            print('mass_dict["{}"] = {}'.format(element, mass_dict[element]))

    return mass_dict

try:
    base = os.path.dirname(os.path.abspath(__file__)) #Cant do this in notebook
except NameError:
    base = os.path.join(os.pardir, 'alphapept')

modfile_path = os.path.join(base, "modifications.tsv")
aafile_path = os.path.join(base, "amino_acids.tsv")

mass_dict = get_mass_dict(modfile=modfile_path, aasfile=aafile_path, verbose=False)

# Cell
import numpy as np
from numba import int32, float32, float64, njit, types
from numba.experimental import jitclass
from numba.typed import Dict

spec = [
    ('m0', float32),
    ('dm', int32),
    ('intensities', float32[:]),
]

@jitclass(spec)
class Isotope:
    """
    Jit-compatible class to store isotopes

    Attributes:
        m0 (int): Mass of pattern
        dm0 (int): dm of pattern (number of isotopes)
        int0 (np.float32[:]): Intensities of pattern
    """
    def __init__(self, m0:int, dm:int, intensities:np.ndarray):
        self.m0 = m0
        self.dm = dm
        self.intensities = intensities

isotopes = Dict.empty(key_type=types.unicode_type, value_type=Isotope.class_type.instance_type)

isotopes["C"] = Isotope(12, 3, np.array([0.9893, 0.0107, 0.0], dtype=np.float32))
isotopes["H"] = Isotope(1.007940, 3,  np.array([0.999885, 0.000115, 0.0], dtype=np.float32))
isotopes["O"] = Isotope(15.9949146221, 3,  np.array([0.99757, 0.00038, 0.00205], dtype=np.float32))
isotopes["N"] = Isotope(14.0030740052, 2,  np.array([0.99636, 0.00364], dtype=np.float32))
isotopes["S"] = Isotope(31.97207069, 4,  np.array([0.9499, 0.0075, 0.0425, 0.0001], dtype=np.float32))

isotopes["I"] = Isotope(126.904473, 1,  np.array([1], dtype=np.float32))
isotopes["K"] = Isotope(38.9637069, 3,  np.array([0.932581, 0.000117, 0.067302], dtype=np.float32))

# Cell
averagine_aa = Dict.empty(key_type=types.unicode_type, value_type=types.float64)

averagine_aa["C"] = 4.9384
averagine_aa["H"] = 7.7583
averagine_aa["N"] = 1.3577
averagine_aa["O"] = 1.4773
averagine_aa["S"] = 0.0417

averagine_avg = 111.1254

# Cell
protease_dict = Dict.empty(key_type=types.unicode_type, value_type=types.unicode_type)

protease_dict["arg-c"] = "R"
protease_dict["asp-n"] = "\w(?=D)"
protease_dict["bnps-skatole"] = "W"
protease_dict["caspase 1"] = "(?<=[FWYL]\w[HAT])D(?=[^PEDQKR])"
protease_dict["caspase 2"] = "(?<=DVA)D(?=[^PEDQKR])"
protease_dict["caspase 3"] = "(?<=DMQ)D(?=[^PEDQKR])"
protease_dict["caspase 4"] = "(?<=LEV)D(?=[^PEDQKR])"
protease_dict["caspase 5"] = "(?<=[LW]EH)D"
protease_dict["caspase 6"] = "(?<=VE[HI])D(?=[^PEDQKR])"
protease_dict["caspase 7"] = "(?<=DEV)D(?=[^PEDQKR])"
protease_dict["caspase 8"] = "(?<=[IL]ET)D(?=[^PEDQKR])"
protease_dict["caspase 9"] = "(?<=LEH)D"
protease_dict["caspase 10"] = "(?<=IEA)D"
protease_dict["chymotrypsin high specificity"] = "([FY](?=[^P]))|(W(?=[^MP]))"
protease_dict["chymotrypsin low specificity"] = "([FLY](?=[^P]))|(W(?=[^MP]))|(M(?=[^PY]))|(H(?=[^DMPW]))"
protease_dict["clostripain"] = "R"
protease_dict["cnbr"] = "M"
protease_dict["enterokinase"] = "(?<=[DE]{3})K"
protease_dict["factor xa"] = "(?<=[AFGILTVM][DE]G)R"
protease_dict["formic acid"] = "D"
protease_dict["glutamyl endopeptidase"] = "E"
protease_dict["granzyme b"] = "(?<=IEP)D"
protease_dict["hydroxylamine"] = "N(?=G)"
protease_dict["iodosobenzoic acid"] = "W"
protease_dict["lysc"] = "K"
protease_dict["lysn"] = "N"
protease_dict["ntcb"] = "\w(?=C)"
protease_dict["pepsin ph1.3"] = "((?<=[^HKR][^P])[^R](?=[FL][^P]))|((?<=[^HKR][^P])[FL](?=\w[^P]))"
protease_dict["pepsin ph2.0"] = "((?<=[^HKR][^P])[^R](?=[FLWY][^P]))|((?<=[^HKR][^P])[FLWY](?=\w[^P]))"
protease_dict["proline endopeptidase"] = "(?<=[HKR])P(?=[^P])"
protease_dict["proteinase k"] = "[AEFILTVWY]"
protease_dict["staphylococcal peptidase i"] = "(?<=[^E])E"
protease_dict["thermolysin"] = "[^DE](?=[AFILMV])"
protease_dict["thrombin"] = "((?<=G)R(?=G))|((?<=[AFGILTVM][AFGILTVWA]P)R(?=[^DE][^DE]))"
protease_dict["trypsin_full"] = "([KR](?=[^P]))|((?<=W)K(?=P))|((?<=M)R(?=P))"
protease_dict["trypsin_exception"] = "((?<=[CD])K(?=D))|((?<=C)K(?=[HY]))|((?<=C)R(?=K))|((?<=R)R(?=[HR]))"
protease_dict["non-specific"] = "()"
protease_dict["trypsin"] = "([KR](?=[^P]))"

# Cell
from numba.typed import Dict
loss_dict = Dict()
loss_dict[''] = 0.0
loss_dict['-H2O'] = 18.01056468346
loss_dict['-NH3'] = 17.03052

# Cell
from collections import namedtuple
import numpy as np
LABEL = namedtuple('label', ['mod_name', 'channels', 'masses', 'reference_channel','mods_fixed_terminal','mods_variable'])

label_dict = {}

label_dict['TMT10plex'] = LABEL('tmt6',
    ['tmt10-126',
 'tmt10-127N',
 'tmt10-127C',
 'tmt10-128N',
 'tmt10-128C',
 'tmt10-129N',
 'tmt10-129C',
 'tmt10-130N',
 'tmt10-130C',
 'tmt10-131',
 'tmt10-131C'],
np.array([126.127726,
 127.124761,
 127.131081,
 128.128116,
 128.134436,
 129.131471,
 129.13779,
 130.134825,
 130.141145,
 131.13818,
 131.144499]),
'tmt10-126',
['tmt6<^'],
['tmt6Y','tmt6K'],
   )