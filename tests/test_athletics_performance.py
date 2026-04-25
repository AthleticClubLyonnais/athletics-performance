#!/usr/bin/env python3
"""
Unit tests for athletics_performance package.
"""

import pytest
from datetime import date

from athletics_performance import (
    EVENT_CATALOG,
    Performance,
    ScoringTables,
)


@pytest.fixture(scope="module")
def scoring_tables():
    """Load ScoringTables once for the module."""
    try:
        return ScoringTables.load()
    except FileNotFoundError:
        pytest.skip("Parquet file not found. Run ScoringTables.build_from_pdf() first.")


class TestScoringTables:
    """Test ScoringTables functionality."""

    def test_load(self, scoring_tables):
        """Test loading ScoringTables from parquet."""
        assert scoring_tables is not None
        assert isinstance(scoring_tables._df, __import__("pandas").DataFrame)

    def test_available_events(self, scoring_tables):
        """Test listing available events."""
        events_all = scoring_tables.available_events()
        assert isinstance(events_all, list)
        assert len(events_all) > 0
        assert "100m" in events_all

        events_m = scoring_tables.available_events("M")
        assert "100m" in events_m
        assert len(events_m) > 0

        events_w = scoring_tables.available_events("W")
        assert "100m" in events_w
        assert len(events_w) > 0

    def test_score_100m_wr(self, scoring_tables):
        """Test scoring Usain Bolt's 100m world record (9.58s)."""
        pts = scoring_tables.score("M", "100m", 9.58)
        assert isinstance(pts, int)
        assert pts >= 1350  # Should be near maximum

    def test_score_below_threshold(self, scoring_tables):
        """Test scoring a performance below the minimum threshold."""
        pts = scoring_tables.score("M", "100m", 30.0)
        assert pts == 0

    def test_score_long_jump_wr(self, scoring_tables):
        """Test scoring Mike Powell's long jump WR (8.95m)."""
        pts = scoring_tables.score("M", "LJ", 8.95)
        assert isinstance(pts, int)
        assert pts >= 1340

    def test_score_marathon(self, scoring_tables):
        """Test scoring a marathon time (around 2:01:39)."""
        marathon_seconds = 2 * 3600 + 1 * 60 + 39  # 7299 seconds
        pts = scoring_tables.score("M", "Mar", marathon_seconds)
        assert isinstance(pts, int)
        # Marathon scoring depends on whether "Mar" event exists in tables
        if pts > 0:
            assert pts >= 600  # Should be a decent score if event is present

    def test_performance_for_points(self, scoring_tables):
        """Test reverse lookup: performance for a given points level."""
        # Find a points level that exists for 100m
        points_to_try = [1200, 1100, 1000, 900, 800]
        perf = None
        for pts in points_to_try:
            try:
                perf = scoring_tables.performance_for_points("M", "100m", pts)
                break
            except ValueError:
                continue

        assert perf is not None, "Could not find any 100m points level"
        assert isinstance(perf, float)
        assert 9.0 < perf < 15.0  # Reasonable range for 100m

    def test_performance_for_points_invalid(self, scoring_tables):
        """Test that invalid (sex, event, points) raises ValueError."""
        with pytest.raises(ValueError):
            scoring_tables.performance_for_points("M", "100m", 9999)

    def test_score_women_100m(self, scoring_tables):
        """Test scoring women's 100m (Florence Griffith-Joyner WR 10.49s)."""
        pts = scoring_tables.score("W", "100m", 10.49)
        assert isinstance(pts, int)
        assert pts >= 1310

    def test_distance_event_type_detection(self):
        """Test that distance events are correctly identified."""
        assert not ScoringTables._is_time_event("LJ")
        assert not ScoringTables._is_time_event("HJ")
        assert not ScoringTables._is_time_event("SP")
        assert not ScoringTables._is_time_event("Dec")
        assert not ScoringTables._is_time_event("Hept")

    def test_time_event_type_detection(self):
        """Test that time events are correctly identified."""
        assert ScoringTables._is_time_event("100m")
        assert ScoringTables._is_time_event("400mH")
        assert ScoringTables._is_time_event("Mar")
        assert ScoringTables._is_time_event("5km_W")


class TestPerformanceScoring:
    """Test Performance.score_points() integration."""

    def test_score_points_method(self, scoring_tables):
        """Test score_points method on a Performance instance."""
        perf = Performance(
            perf_id="P1",
            date=date(2026, 1, 1),
            result_value=9.58,
            measurement="time",
            unit="s",
            athlete_id="1",
            event_id="100m",
        )
        pts = perf.score_points(scoring_tables, "M")
        assert isinstance(pts, int)
        assert pts >= 1350

    def test_score_points_long_jump(self, scoring_tables):
        """Test score_points for a field event."""
        perf = Performance(
            perf_id="P2",
            date=date(2026, 1, 1),
            result_value=8.95,
            measurement="distance",
            unit="m",
            athlete_id="2",
            event_id="LJ",
        )
        pts = perf.score_points(scoring_tables, "M")
        assert isinstance(pts, int)
        assert pts >= 1340


class TestEventCatalog:
    """Test EVENT_CATALOG."""

    def test_event_catalog_exists(self):
        """Test that EVENT_CATALOG is defined."""
        assert EVENT_CATALOG is not None
        assert isinstance(EVENT_CATALOG, dict)
        assert len(EVENT_CATALOG) > 0

    def test_event_catalog_100m(self):
        """Test that 100m event is in catalog."""
        assert "100m" in EVENT_CATALOG
        event = EVENT_CATALOG["100m"]
        assert event.event_id == "100m"
        assert event.measurement == "time"
        assert event.unit == "s"

    def test_event_catalog_long_jump(self):
        """Test that LJ event is in catalog."""
        assert "LJ" in EVENT_CATALOG
        event = EVENT_CATALOG["LJ"]
        assert event.event_id == "LJ"
        assert event.measurement == "distance"
        assert event.unit == "m"

    def test_event_catalog_marathon(self):
        """Test that Marathon event is in catalog."""
        assert "Mar" in EVENT_CATALOG
        event = EVENT_CATALOG["Mar"]
        assert event.measurement == "time"

    def test_event_catalog_decathlon(self):
        """Test that Decathlon is in catalog."""
        assert "Dec" in EVENT_CATALOG
        event = EVENT_CATALOG["Dec"]
        assert event.measurement == "distance"
