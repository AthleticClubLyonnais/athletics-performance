"""
Performance model for athletics results.

This module defines the ``Performance`` class, a normalized domain model that
captures a single athletic result following a relational schema:

Schema
------
- ``perf_id``            - unique identifier for this performance record
- ``athlete_id``         - licence number (FK → Athlete)
- ``event_id``           - event identifier (FK → Event)
- ``date``               - date of the performance (``datetime.date``)
- ``venue``              - competition venue (optional)
- ``result_value``       - standardized numeric result (seconds **or** metres)
- ``measurement``        - ``"time"`` or ``"distance"``
- ``unit``               - ``"s"`` (seconds) or ``"m"`` (metres)
- ``club_id_snapshot``   - club at time of performance (immutable historical record)
- ``category_snapshot``  - age-group category at time of performance
- ``notes``              - free-text notes (optional)

Construction
------------
The constructor accepts either an ``Athlete`` instance **or** a bare
``athlete_id`` string, and either an ``Event`` instance **or** explicit
``event_id`` / ``measurement`` / ``unit`` strings.  ``athlete_category`` is
accepted as an alias for ``category_snapshot`` for convenience.

Raw result strings are automatically converted to the standardized float via
``_parse_result()``.  Dates may be passed as ``datetime.date`` objects or as
strings in ``"dd/mm/YYYY"`` or ``"YYYY-MM-DD"`` format.

Examples
--------
>>> from datetime import date
>>> from athletics_performance import Athlete, Event, Performance
>>> athlete = Athlete(athlete_id="2275784", last_name="Perrin", first_name="Guillaume", yob=1982)
>>> event = Event(event_id="100m", name="100 mètres", measurement="time", unit="s")
>>> Performance(
...     perf_id="P1",
...     date=date(2026, 3, 15),
...     result_value=12.34,
...     measurement="time",
...     unit="s",
...     athlete=athlete,
...     event=event,
...     category_snapshot="M1M",
... )
Performance(perf_id='P1', athlete_id='2275784', event_id='100m', date=datetime.date(2026, 3, 15), result_value=12.34, unit='s')
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional, Union

from .athlete import Athlete
from .event import Event

if TYPE_CHECKING:
    from .scoring_tables import ScoringTables


class Performance:
    """
    Represents a single performance of an athlete in an athletics event.

    See module docstring for the full schema and construction details.
    """

    def __init__(
        self,
        perf_id: str,
        date: Union[date, str],
        result_value: Union[float, str],
        measurement: str,
        unit: str,
        *,
        athlete: Optional[Athlete] = None,
        athlete_id: str = "",
        event: Optional[Event] = None,
        event_id: str = "",
        venue: Optional[str] = None,
        club_id_snapshot: Optional[str] = None,
        category_snapshot: Optional[str] = None,
        athlete_category: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        """
        Parameters
        ----------
        perf_id : str
            Unique identifier for this performance record.
        date : date or str
            Date of the performance. Accepts a ``datetime.date`` object or a
            string in ``"dd/mm/YYYY"`` or ``"YYYY-MM-DD"`` format.
        result_value : float or str
            The performance value. Raw strings (e.g. ``"1:23.45"``, ``"6,78"``)
            are parsed and standardized automatically.
        measurement : {"time", "distance"}
            Type of result. Governs how string values are parsed.
        unit : {"s", "m"}
            Storage unit for the result.
        athlete : Athlete, optional
            If provided, ``athlete_id`` is derived from ``athlete.licence``.
        athlete_id : str, optional
            Licence number; used when *athlete* is not provided.
        event : Event, optional
            If provided, ``event_id``, ``measurement``, and ``unit`` are derived
            from the Event (explicit *measurement*/*unit* arguments take priority).
        event_id : str, optional
            Event identifier; used when *event* is not provided.
        venue : str, optional
            Competition venue name.
        club_id_snapshot : str, optional
            Club identifier captured at the time of the performance.
        category_snapshot : str, optional
            Age-group category captured at the time of the performance.
        athlete_category : str, optional
            Alias for *category_snapshot* (backward-compatible convenience arg).
        notes : str, optional
            Free-text notes.
        """
        # --- athlete resolution ---
        if athlete is not None:
            if not isinstance(athlete, Athlete):
                raise TypeError("athlete must be an Athlete instance.")
            self.athlete_id: str = athlete.licence
        else:
            self.athlete_id = str(athlete_id)

        # --- event resolution (explicit args override Event fields) ---
        if event is not None:
            if not isinstance(event, Event):
                raise TypeError("event must be an Event instance.")
            self.event_id: str = event.event_id
            if not measurement:
                measurement = event.measurement
            if not unit:
                unit = event.unit
        else:
            self.event_id = str(event_id)

        # --- measurement + unit validation ---
        if measurement not in ("time", "distance"):
            raise ValueError("measurement must be 'time' or 'distance'.")
        if unit not in ("s", "m"):
            raise ValueError("unit must be 's' or 'm'.")
        self.measurement: str = measurement
        self.unit: str = unit

        # --- date ---
        if isinstance(date, str):
            self.date = self._parse_date(date)
        elif isinstance(date, datetime):
            self.date = date.date()
        else:
            self.date = date  # already a datetime.date

        # --- result ---
        if isinstance(result_value, str):
            self.result_value: float = self._parse_result(
                result_value, self.measurement
            )
        else:
            self.result_value = float(result_value)

        self.perf_id: str = str(perf_id)
        self.venue: Optional[str] = venue
        self.club_id_snapshot: Optional[str] = club_id_snapshot
        # athlete_category is an alias for category_snapshot
        self.category_snapshot: Optional[str] = category_snapshot or athlete_category
        self.notes: Optional[str] = notes

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """Parse *date_str* in ``"dd/mm/YYYY"`` or ``"YYYY-MM-DD"`` format."""
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        raise ValueError(
            f"Date '{date_str}' must be in 'dd/mm/YYYY' or 'YYYY-MM-DD' format."
        )

    @staticmethod
    def _parse_result(raw: str, measurement: str) -> float:
        """
        Convert a raw result string to a standardized float.

        For timed events (``measurement="time"``):

        - ``"h:mm:ss.cc"`` → total seconds
        - ``"mm:ss.cc"`` or ``"m:ss"`` → total seconds
        - ``"ss.cc"`` or ``"ss,cc"`` → seconds

        For field events (``measurement="distance"``):

        - Returns metres as a float (accepts ``,`` as decimal separator).
        """
        s = raw.strip().replace(",", ".")
        if measurement == "time" and ":" in s:
            parts = s.split(":")
            seconds = float(parts[-1])
            minutes = int(parts[-2])
            hours = int(parts[0]) if len(parts) == 3 else 0
            return hours * 3600 + minutes * 60 + seconds
        return float(s)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def yos(self) -> int:
        """
        Year of season (YOS) derived from the performance date.

        The athletics season runs from 1 September of year N-1 through
        31 August of year N.  A performance dated between those two dates
        belongs to season N.

        Returns
        -------
        int
            The season year N.

        Examples
        --------
        >>> from datetime import date
        >>> p = Performance(perf_id="P1", date=date(2026, 3, 15), result_value=12.34, measurement="time", unit="s", athlete_id="1", event_id="100m")
        >>> p.yos
        2026
        >>> p2 = Performance(perf_id="P2", date=date(2025, 10, 1), result_value=12.34, measurement="time", unit="s", athlete_id="1", event_id="100m")
        >>> p2.yos
        2026
        >>> p3 = Performance(perf_id="P3", date=date(2025, 8, 31), result_value=12.34, measurement="time", unit="s", athlete_id="1", event_id="100m")
        >>> p3.yos
        2025
        """
        # Dates in Sept–Dec belong to season year+1; Jan–Aug to the current year
        if self.date.month >= 9:
            return self.date.year + 1
        return self.date.year

    def convert(self) -> float:
        """
        Return ``result_value`` as a standardized float.

        If ``result_value`` has somehow been stored as a non-float, it is
        parsed and updated in place.  Kept for backward compatibility.
        """
        if not isinstance(self.result_value, float):
            self.result_value = self._parse_result(
                str(self.result_value), self.measurement
            )
        return self.result_value

    def score_points(self, scoring_tables: ScoringTables, sex: str) -> int:
        """
        Return World Athletics points for this performance.

        Parameters
        ----------
        scoring_tables : ScoringTables
            Loaded ScoringTables instance.
        sex : {"M", "W"}
            Athlete sex for table lookup.

        Returns
        -------
        int
            World Athletics points (0 if below minimum threshold).
        """
        return scoring_tables.score(sex, self.event_id, self.result_value)

    def __repr__(self) -> str:
        return (
            f"Performance(perf_id='{self.perf_id}', "
            f"athlete_id='{self.athlete_id}', "
            f"event_id='{self.event_id}', "
            f"date={self.date!r}, "
            f"result_value={self.result_value}, "
            f"unit='{self.unit}')"
        )
