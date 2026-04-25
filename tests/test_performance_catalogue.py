"""Tests for PerformanceCatalogue."""
from datetime import date

import pytest

from athletics_performance import Performance, PerformanceCatalogue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _perf(
    perf_id: str,
    result_value: float,
    measurement: str = "time",
    athlete_id: str = "A1",
    event_id: str = "100m",
    perf_date: date = date(2026, 3, 15),
    category: str | None = None,
    club_id: str | None = None,
) -> Performance:
    unit = "s" if measurement == "time" else "m"
    return Performance(
        perf_id=perf_id,
        date=perf_date,
        result_value=result_value,
        measurement=measurement,
        unit=unit,
        athlete_id=athlete_id,
        event_id=event_id,
        category_snapshot=category,
        club_id_snapshot=club_id,
    )


@pytest.fixture()
def time_catalogue() -> PerformanceCatalogue:
    """Five 100m performances across two athletes."""
    return PerformanceCatalogue([
        _perf("P1", 12.34, athlete_id="A1"),
        _perf("P2", 11.90, athlete_id="A2"),
        _perf("P3", 12.10, athlete_id="A1"),
        _perf("P4", 12.50, athlete_id="A2"),
        _perf("P5", 11.80, athlete_id="A2"),
    ])


@pytest.fixture()
def distance_catalogue() -> PerformanceCatalogue:
    """Three long-jump performances."""
    return PerformanceCatalogue([
        _perf("D1", 6.50, measurement="distance", event_id="LJ"),
        _perf("D2", 7.10, measurement="distance", event_id="LJ"),
        _perf("D3", 6.80, measurement="distance", event_id="LJ"),
    ])


# ---------------------------------------------------------------------------
# Collection protocol
# ---------------------------------------------------------------------------

class TestCollectionProtocol:
    def test_len_empty(self):
        assert len(PerformanceCatalogue()) == 0

    def test_len(self, time_catalogue):
        assert len(time_catalogue) == 5

    def test_iter(self, time_catalogue):
        assert list(time_catalogue) == time_catalogue.to_list()

    def test_repr(self, time_catalogue):
        assert "5 performances" in repr(time_catalogue)

    def test_add(self, time_catalogue):
        extra = PerformanceCatalogue([_perf("P6", 12.00)])
        combined = time_catalogue + extra
        assert len(combined) == 6

    def test_add_wrong_type_returns_not_implemented(self, time_catalogue):
        assert time_catalogue.__add__("not a catalogue") is NotImplemented

    def test_add_in_place(self):
        cat = PerformanceCatalogue()
        p = _perf("P1", 12.00)
        cat.add(p)
        assert len(cat) == 1

    def test_extend(self):
        cat = PerformanceCatalogue()
        perfs = [_perf("P1", 12.00), _perf("P2", 11.80)]
        cat.extend(perfs)
        assert len(cat) == 2

    def test_to_list_is_copy(self, time_catalogue):
        lst = time_catalogue.to_list()
        lst.clear()
        assert len(time_catalogue) == 5


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

class TestFilter:
    def test_filter_athlete_id(self, time_catalogue):
        result = time_catalogue.filter(athlete_id="A1")
        assert len(result) == 2
        assert all(p.athlete_id == "A1" for p in result)

    def test_filter_event_id(self):
        cat = PerformanceCatalogue([
            _perf("P1", 12.0, event_id="100m"),
            _perf("P2", 6.5, measurement="distance", event_id="LJ"),
        ])
        assert len(cat.filter(event_id="100m")) == 1
        assert len(cat.filter(event_id="LJ")) == 1

    def test_filter_date_range(self):
        cat = PerformanceCatalogue([
            _perf("P1", 12.0, perf_date=date(2026, 1, 10)),
            _perf("P2", 11.9, perf_date=date(2026, 3, 15)),
            _perf("P3", 12.1, perf_date=date(2026, 5, 20)),
        ])
        result = cat.filter(date_from=date(2026, 3, 1), date_to=date(2026, 4, 30))
        assert len(result) == 1
        assert result.to_list()[0].perf_id == "P2"

    def test_filter_yos(self):
        cat = PerformanceCatalogue([
            _perf("P1", 12.0, perf_date=date(2025, 5, 1)),   # yos=2025
            _perf("P2", 11.9, perf_date=date(2025, 10, 1)),  # yos=2026
            _perf("P3", 12.1, perf_date=date(2026, 3, 1)),   # yos=2026
        ])
        assert len(cat.filter(yos=2025)) == 1
        assert len(cat.filter(yos=2026)) == 2

    def test_filter_category(self):
        cat = PerformanceCatalogue([
            _perf("P1", 12.0, category="SEF"),
            _perf("P2", 11.9, category="ESF"),
            _perf("P3", 12.1, category="SEF"),
        ])
        assert len(cat.filter(category="SEF")) == 2

    def test_filter_club_id(self):
        cat = PerformanceCatalogue([
            _perf("P1", 12.0, club_id="069001"),
            _perf("P2", 11.9, club_id="069002"),
        ])
        assert len(cat.filter(club_id="069001")) == 1

    def test_filter_combined(self, time_catalogue):
        result = time_catalogue.filter(athlete_id="A2", event_id="100m")
        assert len(result) == 3
        assert all(p.athlete_id == "A2" for p in result)

    def test_filter_no_criteria_returns_all(self, time_catalogue):
        assert len(time_catalogue.filter()) == len(time_catalogue)

    def test_filter_empty_result(self, time_catalogue):
        assert len(time_catalogue.filter(athlete_id="UNKNOWN")) == 0


# ---------------------------------------------------------------------------
# Records and personal bests
# ---------------------------------------------------------------------------

class TestRecord:
    def test_record_time(self, time_catalogue):
        best = time_catalogue.record()
        assert best.perf_id == "P5"  # 11.80 is fastest

    def test_record_distance(self, distance_catalogue):
        best = distance_catalogue.record()
        assert best.perf_id == "D2"  # 7.10 is longest

    def test_record_empty_returns_none(self):
        assert PerformanceCatalogue().record() is None

    def test_record_single_performance(self):
        p = _perf("P1", 12.0)
        assert PerformanceCatalogue([p]).record() is p

    def test_personal_best(self, time_catalogue):
        best_a1 = time_catalogue.personal_best("A1")
        assert best_a1.result_value == 12.10  # min of 12.34, 12.10

        best_a2 = time_catalogue.personal_best("A2")
        assert best_a2.result_value == 11.80  # min of 11.90, 12.50, 11.80

    def test_personal_best_unknown_athlete_returns_none(self, time_catalogue):
        assert time_catalogue.personal_best("UNKNOWN") is None

    def test_personal_bests_count(self, time_catalogue):
        # Two athletes × one event → 2 personal bests
        pb = time_catalogue.personal_bests()
        assert len(pb) == 2

    def test_personal_bests_values(self, time_catalogue):
        pb = time_catalogue.personal_bests()
        values = {p.athlete_id: p.result_value for p in pb}
        assert values["A1"] == 12.10
        assert values["A2"] == 11.80

    def test_personal_bests_multi_event(self):
        cat = PerformanceCatalogue([
            _perf("P1", 12.0, athlete_id="A1", event_id="100m"),
            _perf("P2", 11.5, athlete_id="A1", event_id="100m"),
            _perf("P3", 6.0, measurement="distance", athlete_id="A1", event_id="LJ"),
            _perf("P4", 6.5, measurement="distance", athlete_id="A1", event_id="LJ"),
        ])
        pb = pb = cat.personal_bests()
        assert len(pb) == 2  # one per (A1, 100m) and (A1, LJ)

    def test_records_per_event(self):
        cat = PerformanceCatalogue([
            _perf("P1", 12.0, event_id="100m"),
            _perf("P2", 11.5, event_id="100m"),
            _perf("P3", 6.0, measurement="distance", event_id="LJ"),
            _perf("P4", 6.8, measurement="distance", event_id="LJ"),
        ])
        recs = cat.records()
        assert len(recs) == 2
        rec_map = {p.event_id: p for p in recs}
        assert rec_map["100m"].result_value == 11.5
        assert rec_map["LJ"].result_value == 6.8


# ---------------------------------------------------------------------------
# Ranking and sorting
# ---------------------------------------------------------------------------

class TestRankingAndSorting:
    def test_sorted_time_ascending(self, time_catalogue):
        s = time_catalogue.sorted()
        values = [p.result_value for p in s]
        assert values == sorted(values)  # ascending for time

    def test_sorted_distance_descending(self, distance_catalogue):
        s = distance_catalogue.sorted()
        values = [p.result_value for p in s]
        assert values == sorted(values, reverse=True)  # descending for distance

    def test_sorted_reverse(self, time_catalogue):
        s = time_catalogue.sorted(reverse=True)
        values = [p.result_value for p in s]
        assert values == sorted(values, reverse=True)

    def test_sorted_empty(self):
        assert len(PerformanceCatalogue().sorted()) == 0

    def test_top(self, time_catalogue):
        top3 = time_catalogue.top(3)
        assert len(top3) == 3
        assert top3.to_list()[0].result_value == 11.80  # best first

    def test_top_more_than_available(self, time_catalogue):
        assert len(time_catalogue.top(100)) == len(time_catalogue)

    def test_ranking(self, time_catalogue):
        rank = time_catalogue.ranking()
        assert len(rank) == 2  # one per athlete
        assert rank.to_list()[0].athlete_id == "A2"  # A2 has better PB (11.80)
        assert rank.to_list()[1].athlete_id == "A1"


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------

class TestGroupBy:
    def test_group_by_athlete(self, time_catalogue):
        groups = time_catalogue.group_by("athlete_id")
        assert set(groups.keys()) == {"A1", "A2"}
        assert len(groups["A1"]) == 2
        assert len(groups["A2"]) == 3

    def test_group_by_event(self):
        cat = PerformanceCatalogue([
            _perf("P1", 12.0, event_id="100m"),
            _perf("P2", 11.5, event_id="100m"),
            _perf("P3", 6.0, measurement="distance", event_id="LJ"),
        ])
        groups = cat.group_by("event_id")
        assert len(groups["100m"]) == 2
        assert len(groups["LJ"]) == 1

    def test_group_by_yos(self):
        cat = PerformanceCatalogue([
            _perf("P1", 12.0, perf_date=date(2025, 3, 1)),   # yos=2025
            _perf("P2", 11.9, perf_date=date(2025, 10, 1)),  # yos=2026
            _perf("P3", 12.1, perf_date=date(2026, 4, 1)),   # yos=2026
        ])
        groups = cat.group_by("yos")
        assert len(groups["2025"]) == 1
        assert len(groups["2026"]) == 2


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_empty(self):
        assert PerformanceCatalogue().stats() == {"count": 0}

    def test_stats_single(self):
        cat = PerformanceCatalogue([_perf("P1", 12.0)])
        s = cat.stats()
        assert s["count"] == 1
        assert s["min"] == 12.0
        assert s["max"] == 12.0
        assert s["mean"] == 12.0
        assert "stdev" not in s

    def test_stats_multiple(self, time_catalogue):
        s = time_catalogue.stats()
        assert s["count"] == 5
        assert s["min"] == pytest.approx(11.80)
        assert s["max"] == pytest.approx(12.50)
        assert "stdev" in s
        assert "mean" in s
        assert "median" in s
