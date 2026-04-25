"""
Club model for athletics results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

# Mapping 3-digit department code → (ligue_code, ligue_name)
# Keys are the first 3 characters of a 6-character FFA club_id.
DEPARTMENT_TO_LIGUE: dict[str, Tuple[str, str]] = {
    # Auvergne-Rhône-Alpes
    "001": ("ARA", "Auvergne-Rhône-Alpes"),
    "003": ("ARA", "Auvergne-Rhône-Alpes"),
    "007": ("ARA", "Auvergne-Rhône-Alpes"),
    "015": ("ARA", "Auvergne-Rhône-Alpes"),
    "026": ("ARA", "Auvergne-Rhône-Alpes"),
    "038": ("ARA", "Auvergne-Rhône-Alpes"),
    "042": ("ARA", "Auvergne-Rhône-Alpes"),
    "043": ("ARA", "Auvergne-Rhône-Alpes"),
    "063": ("ARA", "Auvergne-Rhône-Alpes"),
    "069": ("ARA", "Auvergne-Rhône-Alpes"),
    "073": ("ARA", "Auvergne-Rhône-Alpes"),
    "074": ("ARA", "Auvergne-Rhône-Alpes"),
    # Bourgogne-Franche-Comté
    "021": ("BFC", "Bourgogne-Franche-Comté"),
    "025": ("BFC", "Bourgogne-Franche-Comté"),
    "039": ("BFC", "Bourgogne-Franche-Comté"),
    "058": ("BFC", "Bourgogne-Franche-Comté"),
    "070": ("BFC", "Bourgogne-Franche-Comté"),
    "071": ("BFC", "Bourgogne-Franche-Comté"),
    "089": ("BFC", "Bourgogne-Franche-Comté"),
    "090": ("BFC", "Bourgogne-Franche-Comté"),
    # Bretagne
    "022": ("BRE", "Bretagne"),
    "029": ("BRE", "Bretagne"),
    "035": ("BRE", "Bretagne"),
    "056": ("BRE", "Bretagne"),
    # Centre-Val de Loire
    "018": ("CEN", "Centre-Val de Loire"),
    "028": ("CEN", "Centre-Val de Loire"),
    "036": ("CEN", "Centre-Val de Loire"),
    "037": ("CEN", "Centre-Val de Loire"),
    "041": ("CEN", "Centre-Val de Loire"),
    "045": ("CEN", "Centre-Val de Loire"),
    # Corse
    "201": ("COR", "Corse"),
    "202": ("COR", "Corse"),
    # Grand Est
    "008": ("G-E", "Grand Est"),
    "010": ("G-E", "Grand Est"),
    "051": ("G-E", "Grand Est"),
    "052": ("G-E", "Grand Est"),
    "054": ("G-E", "Grand Est"),
    "055": ("G-E", "Grand Est"),
    "057": ("G-E", "Grand Est"),
    "067": ("G-E", "Grand Est"),
    "068": ("G-E", "Grand Est"),
    "088": ("G-E", "Grand Est"),
    # Hauts-de-France
    "002": ("H-F", "Hauts-de-France"),
    "059": ("H-F", "Hauts-de-France"),
    "060": ("H-F", "Hauts-de-France"),
    "062": ("H-F", "Hauts-de-France"),
    "080": ("H-F", "Hauts-de-France"),
    # Île-de-France
    "075": ("I-F", "Île-de-France"),
    "077": ("I-F", "Île-de-France"),
    "078": ("I-F", "Île-de-France"),
    "091": ("I-F", "Île-de-France"),
    "092": ("I-F", "Île-de-France"),
    "093": ("I-F", "Île-de-France"),
    "094": ("I-F", "Île-de-France"),
    "095": ("I-F", "Île-de-France"),
    # Normandie
    "014": ("NOR", "Normandie"),
    "027": ("NOR", "Normandie"),
    "050": ("NOR", "Normandie"),
    "061": ("NOR", "Normandie"),
    "076": ("NOR", "Normandie"),
    # Nouvelle-Aquitaine
    "016": ("N-A", "Nouvelle-Aquitaine"),
    "017": ("N-A", "Nouvelle-Aquitaine"),
    "019": ("N-A", "Nouvelle-Aquitaine"),
    "023": ("N-A", "Nouvelle-Aquitaine"),
    "024": ("N-A", "Nouvelle-Aquitaine"),
    "033": ("N-A", "Nouvelle-Aquitaine"),
    "040": ("N-A", "Nouvelle-Aquitaine"),
    "047": ("N-A", "Nouvelle-Aquitaine"),
    "064": ("N-A", "Nouvelle-Aquitaine"),
    "079": ("N-A", "Nouvelle-Aquitaine"),
    "086": ("N-A", "Nouvelle-Aquitaine"),
    "087": ("N-A", "Nouvelle-Aquitaine"),
    # Occitanie
    "009": ("OCC", "Occitanie"),
    "011": ("OCC", "Occitanie"),
    "012": ("OCC", "Occitanie"),
    "030": ("OCC", "Occitanie"),
    "031": ("OCC", "Occitanie"),
    "032": ("OCC", "Occitanie"),
    "034": ("OCC", "Occitanie"),
    "046": ("OCC", "Occitanie"),
    "048": ("OCC", "Occitanie"),
    "065": ("OCC", "Occitanie"),
    "066": ("OCC", "Occitanie"),
    "081": ("OCC", "Occitanie"),
    "082": ("OCC", "Occitanie"),
    # Provence-Alpes-Côte d'Azur
    "004": ("PCA", "Provence-Alpes-Côte d'Azur"),
    "005": ("PCA", "Provence-Alpes-Côte d'Azur"),
    "006": ("PCA", "Provence-Alpes-Côte d'Azur"),
    "013": ("PCA", "Provence-Alpes-Côte d'Azur"),
    "083": ("PCA", "Provence-Alpes-Côte d'Azur"),
    "084": ("PCA", "Provence-Alpes-Côte d'Azur"),
    # Pays de la Loire
    "044": ("P-L", "Pays de la Loire"),
    "049": ("P-L", "Pays de la Loire"),
    "053": ("P-L", "Pays de la Loire"),
    "072": ("P-L", "Pays de la Loire"),
    "085": ("P-L", "Pays de la Loire"),
    # Overseas
    "971": ("GUA", "Guadeloupe"),
    "972": ("MAR", "Martinique"),
    "973": ("GUY", "Guyane"),
    "974": ("REU", "La Réunion"),
    "976": ("MAY", "Mayotte"),
    "986": ("W-F", "Wallis-et-Futuna"),
    "987": ("P-F", "Polynésie Française"),
    "988": ("N-C", "Nouvelle-Calédonie"),
}


@dataclass(frozen=True)
class Club:
    """
    Represents an athletics club.

    ``dept_code``, ``ligue_code``, and ``ligue_name`` are derived
    automatically from the first 3 characters of ``club_id``:
    ``club_id="069106"`` → ``dept_code="069"``, ``ligue_code="ARA"``,
    ``ligue_name="Auvergne-Rhône-Alpes"``.

    Parameters
    ----------
    club_id : str
        Unique 6-character FFA club identifier.
        The first 3 characters encode the department (e.g. ``"069"``).
    name : str
        Official club name.

    Attributes
    ----------
    dept_code : str
        3-character department code extracted from ``club_id``
        (e.g. ``"069"``).
    ligue_code : str
        Short FFA ligue code (e.g. ``"ARA"``), or ``""`` if unknown.
    ligue_name : str
        Full FFA ligue name (e.g. ``"Auvergne-Rhône-Alpes"``),
        or ``""`` if unknown.

    Raises
    ------
    ValueError
        If ``club_id`` is not exactly 6 characters long.

    Examples
    --------
    >>> Club(club_id="069106", name="ACL")
    Club(club_id='069106', name='ACL', dept_code='069', ligue_code='ARA', ligue_name='Auvergne-Rhône-Alpes')
    >>> Club(club_id="075001", name="Paris AC")
    Club(club_id='075001', name='Paris AC', dept_code='075', ligue_code='I-F', ligue_name='Île-de-France')
    >>> Club(club_id="971001", name="Club Guadeloupe")
    Club(club_id='971001', name='Club Guadeloupe', dept_code='971', ligue_code='GUA', ligue_name='Guadeloupe')
    """

    club_id: str
    name: str
    dept_code: str = field(init=False)
    ligue_code: str = field(init=False)
    ligue_name: str = field(init=False)

    def __post_init__(self) -> None:
        if len(self.club_id) != 6:
            raise ValueError(
                f"club_id must be exactly 6 characters, got {self.club_id!r}."
            )
        dept = self.club_id[:3]
        ligue = DEPARTMENT_TO_LIGUE.get(dept, ("", ""))
        object.__setattr__(self, "dept_code", dept)
        object.__setattr__(self, "ligue_code", ligue[0])
        object.__setattr__(self, "ligue_name", ligue[1])
