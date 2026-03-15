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
