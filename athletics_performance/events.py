"""Event registry and normalization for athletics events.

The EventRegistry provides a canonical mapping of event synonyms (across languages
and sources) to standardized event IDs. This enables consistent event identification
across data imported from different sources (athle.fr, CSVs, APIs, etc.).

Used in the silver layer to normalize event names during data processing.
"""

import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass(frozen=True)
class EventMetadata:
    """Metadata for a standardized athletic event."""

    canonical_id: str
    world_athletics_id: str
    measurement: str  # "time" or "distance"
    unit: str  # "s", "m", "pts"
    description: str


class EventRegistry:
    """Registry for normalizing event names to canonical event IDs.

    Loads event definitions from a YAML configuration file, supporting
    multilingual synonyms (French and English) to handle events from
    different sources.

    Example:
        >>> registry = EventRegistry()
        >>> registry.resolve("longueur")  # French: Long Jump
        'long_jump'
        >>> registry.resolve("LJ")  # World Athletics code
        'long_jump'
        >>> registry.get_metadata("long_jump").measurement
        'distance'
    """

    def __init__(self, yaml_path: Optional[str] = None):
        """Initialize registry with event definitions.

        Args:
            yaml_path: Path to YAML file with event definitions.
                      Defaults to packaged event_registry.yaml.
        """
        if yaml_path is None:
            yaml_path = Path(__file__).parent / "data" / "event_registry.yaml"
        else:
            yaml_path = Path(yaml_path)

        if not yaml_path.exists():
            raise FileNotFoundError(f"Event registry YAML not found: {yaml_path}")

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        self._events: Dict[str, EventMetadata] = {}
        self._synonym_map: Dict[str, str] = {}  # Maps any synonym to canonical ID

        # Build registry from YAML
        if "events" in data:
            for canonical_id, event_def in data["events"].items():
                metadata = EventMetadata(
                    canonical_id=canonical_id,
                    world_athletics_id=event_def.get("world_athletics_id", ""),
                    measurement=event_def.get("measurement", ""),
                    unit=event_def.get("unit", ""),
                    description=event_def.get("description", ""),
                )
                self._events[canonical_id] = metadata

                # Register all synonyms (case-insensitive)
                self._synonym_map[canonical_id.lower()] = canonical_id

                # Register World Athletics ID
                wa_id = event_def.get("world_athletics_id", "")
                if wa_id:
                    self._synonym_map[wa_id.lower()] = canonical_id

                # Register French synonyms
                for synonym in event_def.get("french_synonyms", []):
                    self._synonym_map[synonym.lower()] = canonical_id

                # Register English synonyms
                for synonym in event_def.get("english_synonyms", []):
                    self._synonym_map[synonym.lower()] = canonical_id

    def resolve(self, event_name: str) -> Optional[str]:
        """Resolve an event name (synonym) to canonical event ID.

        Performs case-insensitive lookup supporting French and English synonyms,
        World Athletics codes, and canonical IDs.

        Args:
            event_name: Event name, code, or synonym to resolve.

        Returns:
            Canonical event ID if found, None otherwise.

        Example:
            >>> registry.resolve("100m")
            '100m'
            >>> registry.resolve("100 mètres")
            '100m'
            >>> registry.resolve("LONGUEUR")  # Case-insensitive
            'long_jump'
            >>> registry.resolve("unknown")
            None
        """
        if not event_name:
            return None

        normalized = event_name.strip().lower()
        return self._synonym_map.get(normalized)

    def resolve_strict(self, event_name: str) -> str:
        """Resolve event name, raising error if not found.

        Args:
            event_name: Event name to resolve.

        Returns:
            Canonical event ID.

        Raises:
            ValueError: If event name cannot be resolved.
        """
        result = self.resolve(event_name)
        if result is None:
            raise ValueError(f"Unknown event: {event_name}")
        return result

    def get_metadata(self, canonical_id: str) -> Optional[EventMetadata]:
        """Get metadata for a canonical event ID.

        Args:
            canonical_id: Canonical event ID (e.g., "long_jump").

        Returns:
            EventMetadata if found, None otherwise.
        """
        return self._events.get(canonical_id)

    def get_measurement(self, canonical_id: str) -> Optional[str]:
        """Get measurement type (time/distance/points) for event.

        Args:
            canonical_id: Canonical event ID.

        Returns:
            Measurement type ("time", "distance", "points") or None.
        """
        metadata = self.get_metadata(canonical_id)
        return metadata.measurement if metadata else None

    def get_unit(self, canonical_id: str) -> Optional[str]:
        """Get unit of measurement (s/m/pts) for event.

        Args:
            canonical_id: Canonical event ID.

        Returns:
            Unit ("s", "m", "pts") or None.
        """
        metadata = self.get_metadata(canonical_id)
        return metadata.unit if metadata else None

    def list_events(self) -> list[str]:
        """List all canonical event IDs.

        Returns:
            Sorted list of canonical event IDs.
        """
        return sorted(self._events.keys())

    def __contains__(self, event_name: str) -> bool:
        """Check if event (by name or synonym) is registered.

        Args:
            event_name: Event name or synonym to check.

        Returns:
            True if event is in registry.
        """
        return self.resolve(event_name) is not None
