"""Tests for event registry and normalization."""

import pytest
from pathlib import Path
from athletics_performance.events import EventRegistry, EventMetadata


class TestEventRegistry:
    """Test EventRegistry initialization and basic functionality."""

    @pytest.fixture
    def registry(self):
        """Create registry with default packaged YAML."""
        return EventRegistry()

    def test_registry_loads(self, registry):
        """Registry loads successfully from default YAML."""
        assert registry is not None
        assert len(registry.list_events()) > 0

    def test_registry_contains_common_events(self, registry):
        """Registry contains common athletic events."""
        expected = [
            "100m",
            "200m",
            "400m",
            "800m",
            "1500m",
            "5000m",
            "10000m",
            "marathon",
            "long_jump",
            "high_jump",
            "shot_put",
            "discus",
        ]
        events = registry.list_events()
        for event in expected:
            assert event in events

    def test_resolve_canonical_id(self, registry):
        """Resolve returns canonical ID for canonical input."""
        assert registry.resolve("100m") == "100m"
        assert registry.resolve("long_jump") == "long_jump"

    def test_resolve_french_synonyms(self, registry):
        """Resolve handles French synonyms."""
        assert registry.resolve("longueur") == "long_jump"
        assert registry.resolve("saut en longueur") == "long_jump"
        assert registry.resolve("saut longueur") == "long_jump"

    def test_resolve_english_synonyms(self, registry):
        """Resolve handles English synonyms."""
        assert registry.resolve("long jump") == "long_jump"
        assert registry.resolve("long-jump") == "long_jump"

    def test_resolve_world_athletics_code(self, registry):
        """Resolve handles World Athletics codes."""
        assert registry.resolve("LJ") == "long_jump"
        assert registry.resolve("HJ") == "high_jump"
        assert registry.resolve("SP") == "shot_put"

    def test_resolve_case_insensitive(self, registry):
        """Resolve is case-insensitive."""
        assert registry.resolve("LONGUEUR") == "long_jump"
        assert registry.resolve("LonGueur") == "long_jump"
        assert registry.resolve("100M") == "100m"
        assert registry.resolve("100 M") == "100m"

    def test_resolve_with_whitespace(self, registry):
        """Resolve handles leading/trailing whitespace."""
        assert registry.resolve("  100m  ") == "100m"
        assert registry.resolve("  longueur  ") == "long_jump"

    def test_resolve_unknown_event(self, registry):
        """Resolve returns None for unknown events."""
        assert registry.resolve("unknown") is None
        assert registry.resolve("xyz") is None
        assert registry.resolve("") is None

    def test_resolve_none_input(self, registry):
        """Resolve handles None input gracefully."""
        assert registry.resolve(None) is None

    def test_resolve_strict_valid(self, registry):
        """resolve_strict returns canonical ID for valid events."""
        assert registry.resolve_strict("100m") == "100m"
        assert registry.resolve_strict("longueur") == "long_jump"

    def test_resolve_strict_invalid(self, registry):
        """resolve_strict raises ValueError for unknown events."""
        with pytest.raises(ValueError, match="Unknown event: xyz"):
            registry.resolve_strict("xyz")

    def test_get_metadata_valid(self, registry):
        """get_metadata returns EventMetadata for valid event."""
        metadata = registry.get_metadata("long_jump")
        assert metadata is not None
        assert metadata.canonical_id == "long_jump"
        assert metadata.world_athletics_id == "LJ"
        assert metadata.measurement == "distance"
        assert metadata.unit == "m"
        assert "long jump" in metadata.description.lower()

    def test_get_metadata_invalid(self, registry):
        """get_metadata returns None for unknown event."""
        assert registry.get_metadata("unknown") is None

    def test_get_measurement(self, registry):
        """get_measurement returns correct measurement type."""
        assert registry.get_measurement("100m") == "time"
        assert registry.get_measurement("long_jump") == "distance"
        assert registry.get_measurement("decathlon") == "points"
        assert registry.get_measurement("unknown") is None

    def test_get_unit(self, registry):
        """get_unit returns correct unit."""
        assert registry.get_unit("100m") == "s"
        assert registry.get_unit("long_jump") == "m"
        assert registry.get_unit("decathlon") == "pts"
        assert registry.get_unit("unknown") is None

    def test_contains_operator(self, registry):
        """__contains__ (in operator) works correctly."""
        assert "100m" in registry
        assert "long_jump" in registry
        assert "longueur" in registry
        assert "LJ" in registry
        assert "unknown" not in registry

    def test_list_events_sorted(self, registry):
        """list_events returns sorted list."""
        events = registry.list_events()
        assert events == sorted(events)
        assert len(events) > 0

    def test_hurdles_normalized(self, registry):
        """Hurdle events are correctly normalized."""
        assert registry.resolve("100 haies") == "100m_hurdles"
        assert registry.resolve("110 haies") == "110m_hurdles"
        assert registry.resolve("400 haies") == "400m_hurdles"

    def test_relays_normalized(self, registry):
        """Relay events are correctly normalized."""
        assert registry.resolve("4x100m") == "relay_4x100m"
        assert registry.resolve("4x400m") == "relay_4x400m"
        assert registry.resolve("relais 4x100") == "relay_4x100m"

    def test_steeplechase_normalized(self, registry):
        """Steeplechase is correctly normalized."""
        assert registry.resolve("3000 steeple") == "steeplechase_3000m"
        assert registry.resolve("3000 obstacles") == "steeplechase_3000m"

    def test_field_events_normalized(self, registry):
        """Field events are correctly normalized."""
        # Jumps
        assert registry.resolve("hauteur") == "high_jump"
        assert registry.resolve("saut en hauteur") == "high_jump"
        assert registry.resolve("triple saut") == "triple_jump"
        assert registry.resolve("perche") == "pole_vault"

        # Throws
        assert registry.resolve("poids") == "shot_put"
        assert registry.resolve("disque") == "discus"
        assert registry.resolve("marteau") == "hammer"
        assert registry.resolve("javelot") == "javelin"

    def test_custom_yaml_path(self, tmp_path):
        """EventRegistry can load from custom YAML path."""
        # Create a minimal test YAML
        yaml_file = tmp_path / "test_events.yaml"
        yaml_file.write_text("""events:
  test_event:
    world_athletics_id: "TST"
    measurement: time
    unit: s
    description: "Test event"
    french_synonyms: ["test_fr"]
    english_synonyms: ["test_en"]
""")

        registry = EventRegistry(str(yaml_file))
        assert registry.resolve("test_event") == "test_event"
        assert registry.resolve("test_fr") == "test_event"
        assert registry.resolve("test_en") == "test_event"

    def test_missing_yaml_raises_error(self, tmp_path):
        """EventRegistry raises FileNotFoundError for missing YAML."""
        bad_path = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            EventRegistry(str(bad_path))


class TestEventMetadata:
    """Test EventMetadata dataclass."""

    def test_metadata_frozen(self):
        """EventMetadata is immutable (frozen)."""
        metadata = EventMetadata(
            canonical_id="test",
            world_athletics_id="TST",
            measurement="time",
            unit="s",
            description="Test event",
        )

        with pytest.raises(AttributeError):
            metadata.canonical_id = "modified"

    def test_metadata_fields(self):
        """EventMetadata has correct fields."""
        metadata = EventMetadata(
            canonical_id="100m",
            world_athletics_id="100",
            measurement="time",
            unit="s",
            description="100 meters sprint",
        )

        assert metadata.canonical_id == "100m"
        assert metadata.world_athletics_id == "100"
        assert metadata.measurement == "time"
        assert metadata.unit == "s"
        assert "100 meters" in metadata.description
