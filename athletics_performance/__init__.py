"""
This is a demo package to illustrate how to build and structure a Python package.
It serves as an example for educational purposes only.
"""

from pathlib import Path
from .athlete import Athlete
from .club import Club, DEPARTMENT_TO_LIGUE
from .club_membership import ClubMembership
from .event import Event, EVENT_CATALOG
from .event_mapping import (
    load_event_overrides,
    resolve_event_with_overrides,
    validate_event_mapping,
    apply_event_mapping,
)
from .events import EventRegistry
from .performance import Performance
from .performance_catalogue import PerformanceCatalogue
from .scoring_tables import (
    BEYouthScoringTable,
    MIYouthScoringTable,
    ScoringTable,
    ScoringTableResolver,
    ScoringTables,
    WorldAthletics2025ScoringTable,
)
from .transformations import (
    Correction,
    TransformationRule,
    CorrectionRecord,
    load_transformation_rules,
    identify_performances,
    apply_correction,
    apply_transformations,
    save_corrections_manifest,
    load_corrections_manifest,
    report_transformations,
    verify_reproducibility,
)

__description__ = "Athletics performance scoring and conversion tools"

with open(
    Path(__file__).parent.resolve() / "VERSION",
    encoding="utf-8",
) as version_file:
    __version__ = version_file.read().strip()

__all__ = [
    "Athlete",
    "Club",
    "ClubMembership",
    "Event",
    "EventRegistry",
    "Performance",
    "PerformanceCatalogue",
    "apply_event_mapping",
    "load_event_overrides",
    "resolve_event_with_overrides",
    "validate_event_mapping",
    "BEYouthScoringTable",
    "MIYouthScoringTable",
    "ScoringTable",
    "ScoringTables",
    "ScoringTableResolver",
    "WorldAthletics2025ScoringTable",
    "EVENT_CATALOG",
    "DEPARTMENT_TO_LIGUE",
    "Correction",
    "TransformationRule",
    "CorrectionRecord",
    "load_transformation_rules",
    "identify_performances",
    "apply_correction",
    "apply_transformations",
    "save_corrections_manifest",
    "load_corrections_manifest",
    "report_transformations",
    "verify_reproducibility",
]
