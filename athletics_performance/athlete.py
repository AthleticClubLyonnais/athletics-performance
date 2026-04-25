"""
Athlete model for athletics results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class Athlete:
    """
    Represents an athlete identified by their licence number.

    Instances are immutable (``frozen=True``), hashable, and comparable
    by value, so they can be used as dictionary keys or in sets.

    Parameters
    ----------
    licence : str or int
        Licence number (unique identifier). Integers are automatically
        converted to strings.
    last_name : str
        Athlete's family name.
    first_name : Optional[str]
        Athlete's given name, or ``None`` if not available.
    yob : int
        Year of birth (e.g. ``1982``).
    sex : {"F", "M"}
        Biological sex of the athlete: ``"F"`` for female, ``"M"`` for male.

    Raises
    ------
    ValueError
        If *sex* is not ``"F"`` or ``"M"``.

    Examples
    --------
    >>> Athlete(licence="2275784", last_name="Perrin", first_name="Guillaume", yob=1982, sex="M")
    Athlete(licence='2275784', last_name='Perrin', first_name='Guillaume', yob=1982, sex='M')
    >>> Athlete(licence=9999999, last_name="Dupont", first_name=None, yob=2006, sex="F")
    Athlete(licence='9999999', last_name='Dupont', first_name=None, yob=2006, sex='F')
    """

    licence: str
    last_name: str
    first_name: Optional[str]
    yob: int
    sex: Literal["F", "M"]

    def __post_init__(self) -> None:
        # coerce licence to str (handles int input)
        object.__setattr__(self, "licence", str(self.licence))
        if self.sex not in ("F", "M"):
            raise ValueError(f"sex must be 'F' or 'M', got {self.sex!r}.")

    @property
    def full_name(self) -> str:
        """
        Return the athlete's full name as ``'First Last'``.

        If ``first_name`` is ``None`` or empty, return ``last_name`` alone.

        Examples
        --------
        >>> Athlete(licence="1", last_name="Perrin", first_name="Guillaume", yob=1982, sex="M").full_name
        'Guillaume Perrin'
        >>> Athlete(licence="2", last_name="Dupont", first_name=None, yob=2006, sex="F").full_name
        'Dupont'
        """
        if self.first_name:
            return f"{self.first_name} {self.last_name}"
        return self.last_name

    def category(self, yos: int) -> str:
        """
        Return the full FFA category label for this athlete in season *yos*.

        The label concatenates the age-group code (from :meth:`category_code`)
        with the sex suffix: ``"F"`` for female, ``"M"`` for male —
        except for youth categories (BB, EA, PO, BE, MI) which are
        gender-neutral and returned without a suffix.

        Parameters
        ----------
        yos : int
            Season / competition year.

        Returns
        -------
        str
            Full category label (e.g. ``"SEF"``, ``"M1M"``, ``"CAF"``, ``"MI"``).

        Examples
        --------
        >>> Athlete(licence="1", last_name="X", first_name=None, yob=1982, sex="M").category(2026)
        'M1M'
        >>> Athlete(licence="2", last_name="X", first_name=None, yob=1995, sex="F").category(2026)
        'SEF'
        >>> Athlete(licence="3", last_name="X", first_name=None, yob=2006, sex="M").category(2026)
        'JUM'
        >>> Athlete(licence="4", last_name="X", first_name=None, yob=2012, sex="F").category(2026)
        'MIF'
        """
        return self.category_code(self.yob, yos, self.sex)

    @staticmethod
    def category_code(yob: int, yos: int, sex: str = "") -> str:
        """
        Return the FFA category code for an athlete born in *yob* competing
        in season *yos*, optionally suffixed with *sex*.

        The age-group code is determined by ``age = yos - yob`` according to
        the French Athletics Federation (FFA) classification:

        ======  =======  =========
        Min age  Max age  Code
        ======  =======  =========
        0        6        BB  (Baby)
        7        9        EA  (Éveil Athlétisme)
        10       11       PO  (Poussin)
        12       13       BE  (Benjamin)
        14       15       MI  (Minime)
        16       17       CA  (Cadet)
        18       19       JU  (Junior)
        20       22       ES  (Espoir)
        23       34       SE  (Senior)
        35+      —        M0, M1, M2, … (Master, one bracket per 5 years)
        ======  =======  =========

        Parameters
        ----------
        yob : int
            Year of birth of the athlete.
        yos : int
            Season / competition year.
        sex : {"F", "M", ""}, optional
            When provided, appended to the age-group code (e.g. ``"M"`` →
            ``"SEM"``). Defaults to ``""`` (code only).

        Returns
        -------
        str
            FFA category label (e.g. ``"SE"``, ``"SEM"``, ``"M1F"``).

        Examples
        --------
        >>> Athlete.category_code(1982, 2026)
        'M1'
        >>> Athlete.category_code(1982, 2026, "M")
        'M1M'
        >>> Athlete.category_code(1995, 2026, "F")
        'SEF'
        >>> Athlete.category_code(2012, 2026, "F")
        'MIF'
        >>> Athlete.category_code(2010, 2026)
        'CA'
        >>> Athlete.category_code(2006, 2026, "M")
        'JUM'
        >>> Athlete.category_code(1960, 2026, "F")
        'M6F'
        """
        age = yos - yob

        if age <= 6:
            code = "BB"
        elif age <= 9:
            code = "EA"
        elif age <= 11:
            code = "PO"
        elif age <= 13:
            code = "BE"
        elif age <= 15:
            code = "MI"
        elif age <= 17:
            code = "CA"
        elif age <= 19:
            code = "JU"
        elif age <= 22:
            code = "ES"
        elif age <= 34:
            code = "SE"
        else:
            code = f"M{(age - 35) // 5}"

        return f"{code}{sex}"
