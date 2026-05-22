"""Event mapping validation and correction for silver layer processing.

This module provides tools to validate event name mappings, detect unrecognized
events, generate reports, and apply custom overrides during silver layer
transformation.

Workflow:
1. Import raw data to bronze layer
2. Validate event mappings to silver layer
3. If unrecognized events found: update event_mapping_overrides.yaml
4. Reprocess bronze to silver with corrections (no re-import needed)
"""

from pathlib import Path
from typing import Optional, Dict, Tuple
import yaml
import pandas as pd
from .events import EventRegistry


def load_event_overrides(yaml_path: Optional[str] = None) -> Dict[str, str]:
    """Load custom event name mappings from YAML file.

    Args:
        yaml_path: Path to event_mapping_overrides.yaml.
                  Defaults to packaged file.

    Returns:
        Dictionary mapping raw event names to canonical event IDs.
    """
    if yaml_path is None:
        yaml_path = Path(__file__).parent / "data" / "event_mapping_overrides.yaml"
    else:
        yaml_path = Path(yaml_path)

    if not yaml_path.exists():
        return {}

    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    if not data or "overrides" not in data:
        return {}

    overrides = data.get("overrides", {})
    return overrides if overrides else {}


def resolve_event_with_overrides(
    event_name: str,
    registry: EventRegistry,
    overrides: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[str], str]:
    """Resolve event name using registry + custom overrides.

    Args:
        event_name: Raw event name from data source.
        registry: EventRegistry instance.
        overrides: Custom event name mappings.

    Returns:
        Tuple of (canonical_id, source) where source is "registry", "override", or "unknown".
    """
    if overrides is None:
        overrides = {}

    # Try registry first
    resolved = registry.resolve(event_name)
    if resolved:
        return resolved, "registry"

    # Try overrides
    if event_name in overrides:
        return overrides[event_name], "override"

    return None, "unknown"


def validate_event_mapping(
    df: pd.DataFrame,
    event_column: str = "event_name",
    registry: Optional[EventRegistry] = None,
    overrides: Optional[Dict[str, str]] = None,
) -> Dict:
    """Validate event mappings in a dataframe and generate report.

    Args:
        df: DataFrame with event names to validate.
        event_column: Name of column containing event names.
        registry: EventRegistry instance. Defaults to standard registry.
        overrides: Custom event mappings.

    Returns:
        Report dictionary with statistics and unrecognized events.
    """
    if registry is None:
        registry = EventRegistry()
    if overrides is None:
        overrides = load_event_overrides()

    report = {
        "total_rows": len(df),
        "total_unique_events": df[event_column].nunique(),
        "recognized_rows": 0,
        "recognized_events": {},
        "unrecognized_rows": 0,
        "unrecognized_events": {},
    }

    for event_name in df[event_column].unique():
        if not event_name or pd.isna(event_name):
            continue

        resolved, source = resolve_event_with_overrides(
            event_name, registry, overrides
        )

        count = len(df[df[event_column] == event_name])

        if resolved:
            report["recognized_rows"] += count
            if source not in report["recognized_events"]:
                report["recognized_events"][source] = {}
            if resolved not in report["recognized_events"][source]:
                report["recognized_events"][source][resolved] = []
            report["recognized_events"][source][resolved].append(
                {"raw_name": event_name, "count": count}
            )
        else:
            report["unrecognized_rows"] += count
            report["unrecognized_events"][event_name] = count

    # Add summary stats
    report["recognition_rate"] = (
        report["recognized_rows"] / report["total_rows"] * 100
        if report["total_rows"] > 0
        else 0
    )

    return report


def print_mapping_report(report: Dict) -> None:
    """Pretty-print a mapping validation report.

    Args:
        report: Report dictionary from validate_event_mapping().
    """
    print("\n" + "=" * 70)
    print("EVENT MAPPING VALIDATION REPORT")
    print("=" * 70)

    print(f"\nTotal performances: {report['total_rows']}")
    print(f"Total unique events: {report['total_unique_events']}")
    print(f"Recognition rate: {report['recognition_rate']:.1f}%")

    print(f"\nRecognized: {report['recognized_rows']} rows")
    if report["recognized_events"]:
        for source, events in report["recognized_events"].items():
            print(f"  From {source}:")
            for event_id, mappings in events.items():
                total = sum(m["count"] for m in mappings)
                print(f"    {event_id}: {total} rows")
                for mapping in mappings:
                    if mapping["count"] > 1:
                        print(f"      - '{mapping['raw_name']}' ({mapping['count']}x)")
                    else:
                        print(f"      - '{mapping['raw_name']}'")

    if report["unrecognized_events"]:
        print(f"\nUnrecognized: {report['unrecognized_rows']} rows")
        for event_name, count in sorted(
            report["unrecognized_events"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  - '{event_name}': {count} rows")
        print("\nAction: Add unrecognized events to event_mapping_overrides.yaml")
    else:
        print("\n✓ All events recognized! No corrections needed.")

    print("\n" + "=" * 70 + "\n")


def apply_event_mapping(
    df: pd.DataFrame,
    event_column: str = "event_name",
    registry: Optional[EventRegistry] = None,
    overrides: Optional[Dict[str, str]] = None,
    fail_on_unknown: bool = True,
) -> pd.DataFrame:
    """Apply event mapping to a dataframe, adding event_id and event_source columns.

    Args:
        df: DataFrame with raw event names.
        event_column: Name of column containing raw event names.
        registry: EventRegistry instance.
        overrides: Custom event mappings.
        fail_on_unknown: If True, raise error on unrecognized events.

    Returns:
        DataFrame with added event_id and event_source columns.

    Raises:
        ValueError: If unrecognized events found and fail_on_unknown=True.
    """
    if registry is None:
        registry = EventRegistry()
    if overrides is None:
        overrides = load_event_overrides()

    result = df.copy()

    # Apply mapping
    resolved = result[event_column].apply(
        lambda x: resolve_event_with_overrides(x, registry, overrides)
        if (x and not pd.isna(x))
        else (None, "missing")
    )

    result["event_id"] = resolved.apply(lambda x: x[0])
    result["event_source"] = resolved.apply(lambda x: x[1])

    # Check for unrecognized events
    if fail_on_unknown:
        unrecognized = result[result["event_id"].isna()]
        if len(unrecognized) > 0:
            unknown_events = unrecognized[event_column].unique()
            raise ValueError(
                f"Found {len(unrecognized)} rows with unrecognized events:\n"
                + "\n".join(f"  - '{e}'" for e in unknown_events)
                + "\nAdd these to event_mapping_overrides.yaml and retry."
            )

    return result
