"""
PerformanceCatalogue — an ordered collection of Performance objects.

This module provides the ``PerformanceCatalogue`` class, which groups a set of
``Performance`` records and exposes operations for filtering, record lookup,
personal bests, ranking, grouping, and descriptive statistics.

Examples
--------
>>> from datetime import date
>>> from athletics_performance import Performance, PerformanceCatalogue
>>> p1 = Performance(
...     perf_id="P1", date=date(2026, 3, 15), result_value=12.34,
...     measurement="time", unit="s", athlete_id="A1", event_id="100m",
... )
>>> p2 = Performance(
...     perf_id="P2", date=date(2026, 4, 10), result_value=11.90,
...     measurement="time", unit="s", athlete_id="A2", event_id="100m",
... )
>>> cat = PerformanceCatalogue([p1, p2])
>>> len(cat)
2
>>> cat.record().athlete_id
'A2'
"""
from __future__ import annotations

import statistics as _statistics
from collections import defaultdict
from datetime import date
from typing import Iterable, Iterator

from .performance import Performance


def _is_better(candidate: Performance, current_best: Performance) -> bool:
    """Return True if *candidate* is a better result than *current_best*.

    For time events a lower value wins; for field events a higher value wins.
    Both performances are assumed to share the same measurement type.
    """
    if candidate.measurement == "time":
        return candidate.result_value < current_best.result_value
    return candidate.result_value > current_best.result_value


class PerformanceCatalogue:
    """An ordered collection of Performance objects.

    Supports filtering, record lookup, personal bests, ranking, grouping, and
    basic descriptive statistics.  Most query methods return a **new**
    ``PerformanceCatalogue`` so operations can be chained naturally.

    Parameters
    ----------
    performances : Iterable[Performance], optional
        Initial set of performances.

    Examples
    --------
    >>> from datetime import date
    >>> from athletics_performance import Performance, PerformanceCatalogue
    >>> p = Performance(
    ...     perf_id="P1", date=date(2026, 3, 15), result_value=12.34,
    ...     measurement="time", unit="s", athlete_id="A1", event_id="100m",
    ... )
    >>> cat = PerformanceCatalogue([p])
    >>> len(cat)
    1
    >>> cat.record()
    Performance(perf_id='P1', athlete_id='A1', event_id='100m', date=datetime.date(2026, 3, 15), result_value=12.34, unit='s')
    """

    def __init__(self, performances: Iterable[Performance] = ()) -> None:
        self._performances: list[Performance] = list(performances)

    # ------------------------------------------------------------------ #
    # Collection protocol
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return len(self._performances)

    def __iter__(self) -> Iterator[Performance]:
        return iter(self._performances)

    def __repr__(self) -> str:
        return f"PerformanceCatalogue({len(self._performances)} performances)"

    def __add__(self, other: "PerformanceCatalogue") -> "PerformanceCatalogue":
        """Return the concatenation of two catalogues as a new catalogue."""
        if not isinstance(other, PerformanceCatalogue):
            return NotImplemented
        return PerformanceCatalogue(self._performances + other._performances)

    def add(self, performance: Performance) -> None:
        """Append a single performance in place."""
        self._performances.append(performance)

    def extend(self, performances: Iterable[Performance]) -> None:
        """Append multiple performances in place."""
        self._performances.extend(performances)

    def to_list(self) -> list[Performance]:
        """Return a shallow copy of all performances as a plain list."""
        return list(self._performances)

    # ------------------------------------------------------------------ #
    # Filtering — each method returns a new PerformanceCatalogue
    # ------------------------------------------------------------------ #

    def filter(
        self,
        *,
        athlete_id: str | None = None,
        event_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        yos: int | None = None,
        category: str | None = None,
        club_id: str | None = None,
    ) -> "PerformanceCatalogue":
        """Return a new catalogue containing only performances matching all criteria.

        All parameters are optional; only non-``None`` values are applied.

        Parameters
        ----------
        athlete_id : str, optional
            Keep performances whose ``athlete_id`` equals this value.
        event_id : str, optional
            Keep performances whose ``event_id`` equals this value.
        date_from : date, optional
            Keep performances on or after this date (inclusive).
        date_to : date, optional
            Keep performances on or before this date (inclusive).
        yos : int, optional
            Keep performances belonging to the given athletics season year.
        category : str, optional
            Keep performances whose ``category_snapshot`` equals this value.
        club_id : str, optional
            Keep performances whose ``club_id_snapshot`` equals this value.
        """
        result = self._performances
        if athlete_id is not None:
            result = [p for p in result if p.athlete_id == athlete_id]
        if event_id is not None:
            result = [p for p in result if p.event_id == event_id]
        if date_from is not None:
            result = [p for p in result if p.date >= date_from]
        if date_to is not None:
            result = [p for p in result if p.date <= date_to]
        if yos is not None:
            result = [p for p in result if p.yos == yos]
        if category is not None:
            result = [p for p in result if p.category_snapshot == category]
        if club_id is not None:
            result = [p for p in result if p.club_id_snapshot == club_id]
        return PerformanceCatalogue(result)

    # ------------------------------------------------------------------ #
    # Records and personal bests
    # ------------------------------------------------------------------ #

    def record(self) -> Performance | None:
        """Return the single best performance in the catalogue.

        For time events the lowest ``result_value`` wins; for field events the
        highest wins.  Call this after filtering to a single event for a
        meaningful result.

        Returns ``None`` when the catalogue is empty.
        """
        if not self._performances:
            return None
        best = self._performances[0]
        for p in self._performances[1:]:
            if _is_better(p, best):
                best = p
        return best

    def personal_best(self, athlete_id: str) -> Performance | None:
        """Return the best performance for one athlete.

        Equivalent to ``self.filter(athlete_id=athlete_id).record()``.
        Meaningful when the catalogue is already filtered to a single event.
        """
        return self.filter(athlete_id=athlete_id).record()

    def personal_bests(self) -> "PerformanceCatalogue":
        """Return one performance per *(athlete_id, event_id)* pair.

        Keeps only each athlete's best performance per event.  Useful for
        building season rankings where each athlete appears at most once.
        """
        bests: dict[tuple[str, str], Performance] = {}
        for p in self._performances:
            key = (p.athlete_id, p.event_id)
            if key not in bests or _is_better(p, bests[key]):
                bests[key] = p
        return PerformanceCatalogue(bests.values())

    def records(self) -> "PerformanceCatalogue":
        """Return the best performance per event_id — one record per event."""
        best_per_event: dict[str, Performance] = {}
        for p in self._performances:
            if p.event_id not in best_per_event or _is_better(p, best_per_event[p.event_id]):
                best_per_event[p.event_id] = p
        return PerformanceCatalogue(best_per_event.values())

    # ------------------------------------------------------------------ #
    # Ranking and sorting
    # ------------------------------------------------------------------ #

    def sorted(self, *, reverse: bool = False) -> "PerformanceCatalogue":
        """Return a new catalogue sorted best-first by result value.

        For time events performances are sorted ascending (lower is better).
        For field events they are sorted descending (higher is better).
        Pass ``reverse=True`` to invert the order.

        Sorting is only meaningful when the catalogue contains a single event
        type (same ``measurement``).
        """
        if not self._performances:
            return PerformanceCatalogue()
        best_first_descending = self._performances[0].measurement == "distance"
        return PerformanceCatalogue(
            sorted(
                self._performances,
                key=lambda p: p.result_value,
                reverse=best_first_descending ^ reverse,
            )
        )

    def top(self, n: int) -> "PerformanceCatalogue":
        """Return the top *n* performances, sorted best-first.

        Meaningful when the catalogue is filtered to a single event.
        """
        return PerformanceCatalogue(self.sorted().to_list()[:n])

    def ranking(self) -> "PerformanceCatalogue":
        """Return one personal-best per athlete, sorted best-first.

        Combines :meth:`personal_bests` and :meth:`sorted` to produce a
        ranked list.  Apply :meth:`filter` first to scope the catalogue to a
        single event and, optionally, a season.
        """
        return self.personal_bests().sorted()

    # ------------------------------------------------------------------ #
    # Grouping
    # ------------------------------------------------------------------ #

    def group_by(self, key: str) -> dict[str, "PerformanceCatalogue"]:
        """Group performances by a ``Performance`` attribute name.

        Parameters
        ----------
        key : str
            A ``Performance`` attribute name, e.g. ``"athlete_id"``,
            ``"event_id"``, ``"category_snapshot"``.

        Returns
        -------
        dict[str, PerformanceCatalogue]
            Keys are the stringified attribute values; values are sub-catalogues.
        """
        groups: dict[str, list[Performance]] = defaultdict(list)
        for p in self._performances:
            value = str(getattr(p, key, None) or "")
            groups[value].append(p)
        return {k: PerformanceCatalogue(v) for k, v in groups.items()}

    # ------------------------------------------------------------------ #
    # Statistics
    # ------------------------------------------------------------------ #

    def stats(self) -> dict[str, float | int]:
        """Return basic descriptive statistics over ``result_value``.

        Meaningful when the catalogue is filtered to a single event, since
        comparing time values with distances is nonsensical.

        Returns
        -------
        dict
            Keys: ``count``, ``min``, ``max``, ``mean``, ``median``, and
            ``stdev`` (only present when ``count >= 2``).
            Returns ``{"count": 0}`` for an empty catalogue.
        """
        values = [p.result_value for p in self._performances]
        if not values:
            return {"count": 0}
        result: dict[str, float | int] = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": _statistics.mean(values),
            "median": _statistics.median(values),
        }
        if len(values) >= 2:
            result["stdev"] = _statistics.stdev(values)
        return result
