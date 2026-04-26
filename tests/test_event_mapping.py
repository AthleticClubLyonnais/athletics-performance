"""Tests for event mapping validation and correction."""

import pytest
import pandas as pd
from pathlib import Path
from athletics_performance.event_mapping import (
    load_event_overrides,
    resolve_event_with_overrides,
    validate_event_mapping,
    apply_event_mapping,
)
from athletics_performance.events import EventRegistry


class TestLoadEventOverrides:
    """Test loading event mapping overrides."""

    def test_load_empty_overrides(self):
        """Load returns empty dict if file doesn't exist."""
        overrides = load_event_overrides("/nonexistent/path.yaml")
        assert overrides == {}

    def test_load_packaged_overrides(self):
        """Load returns dict (may be empty if no overrides defined)."""
        overrides = load_event_overrides()
        assert isinstance(overrides, dict)

    def test_load_custom_overrides(self, tmp_path):
        """Load custom overrides from file."""
        yaml_file = tmp_path / "custom_overrides.yaml"
        yaml_file.write_text("""overrides:
  "Saut Hauteur": "high_jump"
  "Disq": "discus"
  "100m plat": "100m"
""")

        overrides = load_event_overrides(str(yaml_file))
        assert overrides["Saut Hauteur"] == "high_jump"
        assert overrides["Disq"] == "discus"
        assert overrides["100m plat"] == "100m"


class TestResolveEventWithOverrides:
    """Test event resolution with fallback to overrides."""

    @pytest.fixture
    def registry(self):
        return EventRegistry()

    def test_resolve_from_registry(self, registry):
        """Resolve returns registry result when available."""
        event_id, source = resolve_event_with_overrides("longueur", registry)
        assert event_id == "long_jump"
        assert source == "registry"

    def test_resolve_from_overrides(self, registry):
        """Resolve uses overrides when registry doesn't match."""
        overrides = {"Custom Event": "high_jump"}
        event_id, source = resolve_event_with_overrides(
            "Custom Event", registry, overrides
        )
        assert event_id == "high_jump"
        assert source == "override"

    def test_resolve_unknown(self, registry):
        """Resolve returns None for unknown events."""
        event_id, source = resolve_event_with_overrides("unknown_event", registry)
        assert event_id is None
        assert source == "unknown"

    def test_registry_takes_precedence(self, registry):
        """Registry result takes precedence over overrides."""
        overrides = {"100m": "other_event"}
        event_id, source = resolve_event_with_overrides("100m", registry, overrides)
        assert event_id == "100m"
        assert source == "registry"


class TestValidateEventMapping:
    """Test event mapping validation and reporting."""

    @pytest.fixture
    def sample_df(self):
        """Create sample dataframe with various event names."""
        return pd.DataFrame({
            "perf_id": ["p1", "p2", "p3", "p4", "p5", "p6"],
            "event_name": [
                "100m",           # Registry
                "100m",           # Registry (duplicate)
                "longueur",       # Registry (French)
                "hauteur",        # Registry (French)
                "Unknown Event",  # Unrecognized
                "Typo Event",     # Unrecognized
            ],
        })

    def test_validate_all_recognized(self):
        """Validate returns correct stats when all events recognized."""
        df = pd.DataFrame({
            "event_name": ["100m", "100m", "longueur", "hauteur"],
        })

        report = validate_event_mapping(df)

        assert report["total_rows"] == 4
        assert report["total_unique_events"] == 3
        assert report["recognized_rows"] == 4
        assert report["unrecognized_rows"] == 0
        assert report["recognition_rate"] == 100.0

    def test_validate_partial_recognition(self, sample_df):
        """Validate reports unrecognized events."""
        report = validate_event_mapping(sample_df)

        assert report["total_rows"] == 6
        assert report["total_unique_events"] == 5  # 100m appears twice
        assert report["recognized_rows"] == 4
        assert report["unrecognized_rows"] == 2
        assert report["recognition_rate"] == pytest.approx(66.67, rel=1)
        assert "Unknown Event" in report["unrecognized_events"]
        assert "Typo Event" in report["unrecognized_events"]

    def test_validate_with_overrides(self, sample_df):
        """Validate uses overrides to resolve additional events."""
        overrides = {
            "Unknown Event": "100m",
            "Typo Event": "discus",
        }
        report = validate_event_mapping(sample_df, overrides=overrides)

        assert report["recognized_rows"] == 6
        assert report["unrecognized_rows"] == 0
        assert report["recognition_rate"] == 100.0

    def test_validate_reports_by_source(self):
        """Validate distinguishes registry vs override sources."""
        df = pd.DataFrame({
            "event_name": ["100m", "Custom Event"],
        })
        overrides = {"Custom Event": "discus"}

        report = validate_event_mapping(df, overrides=overrides)

        assert "registry" in report["recognized_events"]
        assert "override" in report["recognized_events"]
        assert "100m" in report["recognized_events"]["registry"]
        assert "discus" in report["recognized_events"]["override"]


class TestApplyEventMapping:
    """Test applying event mappings to dataframe."""

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            "perf_id": ["p1", "p2", "p3"],
            "event_name": ["100m", "longueur", "hauteur"],
        })

    def test_apply_adds_columns(self, sample_df):
        """Apply adds event_id and event_source columns."""
        result = apply_event_mapping(sample_df, fail_on_unknown=False)

        assert "event_id" in result.columns
        assert "event_source" in result.columns
        assert len(result) == len(sample_df)

    def test_apply_maps_correctly(self, sample_df):
        """Apply correctly maps events."""
        result = apply_event_mapping(sample_df, fail_on_unknown=False)

        assert result.iloc[0]["event_id"] == "100m"
        assert result.iloc[1]["event_id"] == "long_jump"
        assert result.iloc[2]["event_id"] == "high_jump"
        assert all(result["event_source"] == "registry")

    def test_apply_with_overrides(self, sample_df):
        """Apply uses custom overrides."""
        overrides = {"100m": "custom_event"}
        result = apply_event_mapping(
            sample_df, overrides=overrides, fail_on_unknown=False
        )

        assert result.iloc[0]["event_id"] == "100m"
        assert result.iloc[0]["event_source"] == "registry"

    def test_apply_fail_on_unknown_true(self):
        """Apply raises error on unknown events when fail_on_unknown=True."""
        df = pd.DataFrame({
            "event_name": ["100m", "Unknown Event"],
        })

        with pytest.raises(ValueError, match="unrecognized events"):
            apply_event_mapping(df, fail_on_unknown=True)

    def test_apply_fail_on_unknown_false(self):
        """Apply doesn't raise when fail_on_unknown=False."""
        df = pd.DataFrame({
            "event_name": ["100m", "Unknown Event"],
        })

        result = apply_event_mapping(df, fail_on_unknown=False)
        assert len(result) == 2
        assert pd.isna(result.iloc[1]["event_id"])
        assert result.iloc[1]["event_source"] == "unknown"

    def test_apply_handles_missing_values(self):
        """Apply handles missing/null event names."""
        df = pd.DataFrame({
            "event_name": ["100m", None, "hauteur", pd.NA],
        })

        result = apply_event_mapping(df, fail_on_unknown=False)
        assert result.iloc[1]["event_source"] == "missing"
        assert result.iloc[3]["event_source"] == "missing"


class TestIntegration:
    """Integration tests for complete workflow."""

    def test_workflow_detect_unrecognized(self, tmp_path):
        """Complete workflow: detect unrecognized events."""
        # Simulate raw data with unrecognized events
        df = pd.DataFrame({
            "perf_id": ["p1", "p2", "p3", "p4", "p5"],
            "athlete": ["A", "B", "C", "D", "E"],
            "event_name": [
                "100m",
                "100m",
                "Custom Event 1",  # Unrecognized
                "Custom Event 2",  # Unrecognized
                "hauteur",         # Recognized
            ],
        })

        # Validate - should detect unrecognized
        report = validate_event_mapping(df)
        assert report["unrecognized_rows"] == 2
        assert "Custom Event 1" in report["unrecognized_events"]
        assert "Custom Event 2" in report["unrecognized_events"]

    def test_workflow_correct_and_reprocess(self, tmp_path):
        """Complete workflow: correct and reprocess."""
        # Create overrides file
        overrides_file = tmp_path / "overrides.yaml"
        overrides_file.write_text("""overrides:
  "Saut Hauteur": "high_jump"
  "Disq": "discus"
""")

        # Raw data with errors
        df = pd.DataFrame({
            "perf_id": ["p1", "p2", "p3", "p4"],
            "event_name": [
                "100m",
                "Saut Hauteur",
                "Disq",
                "hauteur",
            ],
        })

        # Apply mapping with overrides
        result = apply_event_mapping(
            df,
            overrides=load_event_overrides(str(overrides_file)),
            fail_on_unknown=False,
        )

        # Verify all mapped correctly
        assert result["event_id"].isna().sum() == 0
        assert result.iloc[1]["event_id"] == "high_jump"
        assert result.iloc[2]["event_id"] == "discus"
