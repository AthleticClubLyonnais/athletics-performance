"""
Event model for athletics results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Event:
    """
    Represents an athletics event (discipline).

    Parameters
    ----------
    event_id : str
        Unique event identifier (e.g. ``"100m"``, ``"HJ"``, ``"JT"``).
    name : str
        Full event name (e.g. ``"100 mètres"``, ``"Saut en hauteur"``).
    measurement : {"time", "distance"}
        Whether the result is a time or a distance.
    unit : {"s", "m"}
        Standard storage unit: ``"s"`` for seconds (timed events),
        ``"m"`` for metres (field events).

    Raises
    ------
    ValueError
        If *measurement* or *unit* is not one of the accepted values.

    Examples
    --------
    >>> Event(event_id="100m", name="100 mètres", measurement="time", unit="s")
    Event(event_id='100m', name='100 mètres', measurement='time', unit='s')
    >>> Event(event_id="LJ", name="Saut en longueur", measurement="distance", unit="m")
    Event(event_id='LJ', name='Saut en longueur', measurement='distance', unit='m')
    """

    event_id: str
    name: str
    measurement: Literal["time", "distance"]
    unit: Literal["s", "m"]

    def __post_init__(self) -> None:
        if self.measurement not in ("time", "distance"):
            raise ValueError("measurement must be 'time' or 'distance'.")
        if self.unit not in ("s", "m"):
            raise ValueError("unit must be 's' or 'm'.")


EVENT_CATALOG: dict[str, Event] = {
    "50m": Event("50m", "50 mètres", "time", "s"),
    "55m": Event("55m", "55 mètres", "time", "s"),
    "60m": Event("60m", "60 mètres", "time", "s"),
    "100m": Event("100m", "100 mètres", "time", "s"),
    "200m": Event("200m", "200 mètres", "time", "s"),
    "200m_sh": Event("200m_sh", "200 mètres (indoor)", "time", "s"),
    "300m": Event("300m", "300 mètres", "time", "s"),
    "300m_sh": Event("300m_sh", "300 mètres (indoor)", "time", "s"),
    "400m": Event("400m", "400 mètres", "time", "s"),
    "400m_sh": Event("400m_sh", "400 mètres (indoor)", "time", "s"),
    "500m": Event("500m", "500 mètres", "time", "s"),
    "500m_sh": Event("500m_sh", "500 mètres (indoor)", "time", "s"),
    "50mH": Event("50mH", "50m haies", "time", "s"),
    "55mH": Event("55mH", "55m haies", "time", "s"),
    "60mH": Event("60mH", "60m haies", "time", "s"),
    "100mH": Event("100mH", "100m haies", "time", "s"),
    "110mH": Event("110mH", "110m haies", "time", "s"),
    "300mH": Event("300mH", "300m haies", "time", "s"),
    "400mH": Event("400mH", "400m haies", "time", "s"),
    "4x100m": Event("4x100m", "4x100m relais", "time", "s"),
    "4x200m": Event("4x200m", "4x200m relais", "time", "s"),
    "4x200m_sh": Event("4x200m_sh", "4x200m relais (indoor)", "time", "s"),
    "4x400m": Event("4x400m", "4x400m relais", "time", "s"),
    "4x400m_sh": Event("4x400m_sh", "4x400m relais (indoor)", "time", "s"),
    "4x400mix": Event("4x400mix", "4x400m relais mixte", "time", "s"),
    "4x400mix_sh": Event("4x400mix_sh", "4x400m relais mixte (indoor)", "time", "s"),
    "600m": Event("600m", "600 mètres", "time", "s"),
    "600m_sh": Event("600m_sh", "600 mètres (indoor)", "time", "s"),
    "800m": Event("800m", "800 mètres", "time", "s"),
    "800m_sh": Event("800m_sh", "800 mètres (indoor)", "time", "s"),
    "1000m": Event("1000m", "1000 mètres", "time", "s"),
    "1000m_sh": Event("1000m_sh", "1000 mètres (indoor)", "time", "s"),
    "1500m": Event("1500m", "1500 mètres", "time", "s"),
    "1500m_sh": Event("1500m_sh", "1500 mètres (indoor)", "time", "s"),
    "1_Mile": Event("1_Mile", "1 mile", "time", "s"),
    "1_Mile_sh": Event("1_Mile_sh", "1 mile (indoor)", "time", "s"),
    "2000m": Event("2000m", "2000 mètres", "time", "s"),
    "2000m_sh": Event("2000m_sh", "2000 mètres (indoor)", "time", "s"),
    "3000m": Event("3000m", "3000 mètres", "time", "s"),
    "3000m_sh": Event("3000m_sh", "3000 mètres (indoor)", "time", "s"),
    "2_Miles": Event("2_Miles", "2 miles", "time", "s"),
    "2_Miles_sh": Event("2_Miles_sh", "2 miles (indoor)", "time", "s"),
    "5000m": Event("5000m", "5000 mètres", "time", "s"),
    "5000m_sh": Event("5000m_sh", "5000 mètres (indoor)", "time", "s"),
    "10000m": Event("10000m", "10000 mètres", "time", "s"),
    "10000m_sh": Event("10000m_sh", "10000 mètres (indoor)", "time", "s"),
    "5km": Event("5km", "5 km (sur route)", "time", "s"),
    "5km_sh": Event("5km_sh", "5 km (indoor)", "time", "s"),
    "10km": Event("10km", "10 km (sur route)", "time", "s"),
    "10km_sh": Event("10km_sh", "10 km (indoor)", "time", "s"),
    "15km": Event("15km", "15 km (sur route)", "time", "s"),
    "20km": Event("20km", "20 km (sur route)", "time", "s"),
    "HM": Event("HM", "Semi-marathon", "time", "s"),
    "25km": Event("25km", "25 km (sur route)", "time", "s"),
    "30km": Event("30km", "30 km (sur route)", "time", "s"),
    "Mar": Event("Mar", "Marathon", "time", "s"),
    "100km": Event("100km", "100 km (sur route)", "time", "s"),
    "3km_W": Event("3km_W", "3 km marche (sur route)", "time", "s"),
    "5km_W": Event("5km_W", "5 km marche (sur route)", "time", "s"),
    "10km_W": Event("10km_W", "10 km marche (sur route)", "time", "s"),
    "15km_W": Event("15km_W", "15 km marche (sur route)", "time", "s"),
    "20km_W": Event("20km_W", "20 km marche (sur route)", "time", "s"),
    "30km_W": Event("30km_W", "30 km marche (sur route)", "time", "s"),
    "35km_W": Event("35km_W", "35 km marche (sur route)", "time", "s"),
    "50km_W": Event("50km_W", "50 km marche (sur route)", "time", "s"),
    "3000m_W": Event("3000m_W", "3000 m marche (piste)", "time", "s"),
    "5000m_W": Event("5000m_W", "5000 m marche (piste)", "time", "s"),
    "10000m_W": Event("10000m_W", "10000 m marche (piste)", "time", "s"),
    "15000m_W": Event("15000m_W", "15000 m marche (piste)", "time", "s"),
    "20000m_W": Event("20000m_W", "20000 m marche (piste)", "time", "s"),
    "30000m_W": Event("30000m_W", "30000 m marche (piste)", "time", "s"),
    "50000m_W": Event("50000m_W", "50000 m marche (piste)", "time", "s"),
    "HJ": Event("HJ", "Saut en hauteur", "distance", "m"),
    "PV": Event("PV", "Saut à la perche", "distance", "m"),
    "LJ": Event("LJ", "Saut en longueur", "distance", "m"),
    "TJ": Event("TJ", "Triple saut", "distance", "m"),
    "SP": Event("SP", "Lancer de poids", "distance", "m"),
    "DT": Event("DT", "Lancer du disque", "distance", "m"),
    "HT": Event("HT", "Lancer du marteau", "distance", "m"),
    "JT": Event("JT", "Lancer du javelot", "distance", "m"),
    "WT": Event("WT", "Lancer du poids (indoor)", "distance", "m"),
    "Dec": Event("Dec", "Décathlon", "distance", "m"),
    "Hept": Event("Hept", "Heptathlon", "distance", "m"),
    "Pent_sh": Event("Pent_sh", "Pentathlon (indoor)", "distance", "m"),
    "Hept_sh": Event("Hept_sh", "Heptathlon (indoor)", "distance", "m"),
}
