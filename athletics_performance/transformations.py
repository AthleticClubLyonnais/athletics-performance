"""Silver layer data transformations and corrections.

This module provides tools to apply tracked, reproducible transformations to
performance data during the bronze→silver conversion. All transformations are:

- Declarative (defined in YAML, stored with data)
- Reproducible (same input + rules = identical output)
- Audited (corrections manifest tracks all changes)
- Data-focused (stored with parquet, not in git)

Transformations are stored alongside bronze/silver parquet files, not in git,
since they are data artifacts, not code.

Example:
    bronze_transformations.yaml (stored in data store):
        transformations:
          - rule_id: "fix_date_error"
            applies_to:
              selector: "perf_ids"
              values: ["perf_001", "perf_002"]
            corrections:
              - field: "date"
                old_value: "2025-03-15"
                new_value: "2026-03-15"

    Then during bronze→silver:
        rules = load_transformation_rules(yaml_content)
        df_silver, manifest = apply_transformations(df_bronze, rules)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Optional, Dict, List, Union
from pathlib import Path

import yaml
import pandas as pd


@dataclass
class Correction:
    """A single field correction."""

    field: str
    old_value: Any = None
    new_value: Any = None
    operation: Optional[str] = None  # "divide", "multiply", "replace", etc.
    operand: Optional[float] = None  # For operations like divide/multiply
    description: Optional[str] = None


@dataclass
class TransformationRule:
    """A single transformation rule with metadata."""

    rule_id: str
    description: str
    applies_to: Dict[str, Any]  # Selector logic
    corrections: List[Correction] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrectionRecord:
    """Record of a single correction applied to a performance."""

    rule_id: str
    perf_id: str
    field: str
    old_value: Any
    new_value: Any
    applied_date: datetime
    reviewer: str = ""
    source_file: str = ""


def load_transformation_rules(yaml_content: str) -> List[TransformationRule]:
    """Load transformation rules from YAML content.

    Args:
        yaml_content: YAML string containing transformation rules.

    Returns:
        List of TransformationRule objects.

    Raises:
        ValueError: If YAML is invalid or missing required fields.
    """
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in transformation rules: {e}")

    if not data or "transformations" not in data:
        return []

    rules = []
    for rule_data in data.get("transformations", []):
        # Parse corrections
        corrections = []
        for corr_data in rule_data.get("corrections", []):
            corr = Correction(
                field=corr_data.get("field"),
                old_value=corr_data.get("old_value"),
                new_value=corr_data.get("new_value"),
                operation=corr_data.get("operation"),
                operand=corr_data.get("operand"),
                description=corr_data.get("description"),
            )
            corrections.append(corr)

        rule = TransformationRule(
            rule_id=rule_data.get("rule_id"),
            description=rule_data.get("description", ""),
            applies_to=rule_data.get("applies_to", {}),
            corrections=corrections,
            metadata=rule_data.get("metadata", {}),
        )
        rules.append(rule)

    return rules


def identify_performances(
    df: pd.DataFrame, selector: Dict[str, Any]
) -> List[str]:
    """Identify which performances match a selector.

    Supports:
    - selector: "perf_ids" with values list
    - selector: "condition" with complex matching logic

    Args:
        df: Performance dataframe.
        selector: Selector specification from transformation rule.

    Returns:
        List of perf_id values that match the selector.
    """
    selector_type = selector.get("selector", "perf_ids")

    if selector_type == "perf_ids":
        # Simple list of perf_ids
        values = selector.get("values", [])
        # Filter to only those that exist in df
        return [v for v in values if v in df["perf_id"].values]

    elif selector_type == "condition":
        # Complex condition matching
        match_specs = selector.get("match", [])
        result_df = df.copy()

        for spec in match_specs:
            field = spec.get("field")
            if "equals" in spec:
                result_df = result_df[result_df[field] == spec["equals"]]
            elif "gt" in spec:
                result_df = result_df[result_df[field] > spec["gt"]]
            elif "lt" in spec:
                result_df = result_df[result_df[field] < spec["lt"]]
            elif "gte" in spec:
                result_df = result_df[result_df[field] >= spec["gte"]]
            elif "lte" in spec:
                result_df = result_df[result_df[field] <= spec["lte"]]
            elif "contains" in spec:
                result_df = result_df[
                    result_df[field].str.contains(spec["contains"], na=False)
                ]

        return result_df["perf_id"].tolist()

    return []


def apply_correction(
    df: pd.DataFrame, perf_id: str, correction: Correction
) -> Any:
    """Apply a single correction to a performance field.

    Args:
        df: Dataframe (for reference).
        perf_id: Performance ID to correct.
        correction: Correction specification.

    Returns:
        New value for the field.
    """
    perf_row = df[df["perf_id"] == perf_id]
    if len(perf_row) == 0:
        return None

    old_value = perf_row[correction.field].iloc[0]

    # Simple replacement
    if correction.new_value is not None:
        return correction.new_value

    # Operation-based (divide, multiply, etc.)
    if correction.operation and correction.operand:
        if correction.operation == "divide":
            return old_value / correction.operand
        elif correction.operation == "multiply":
            return old_value * correction.operand

    return old_value


def apply_transformations(
    df_bronze: pd.DataFrame,
    rules: List[TransformationRule],
    track_changes: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply transformation rules to bronze data.

    Args:
        df_bronze: Bronze layer dataframe (will not be modified).
        rules: List of transformation rules to apply.
        track_changes: Whether to track changes in manifest.

    Returns:
        Tuple of (transformed_df, corrections_manifest).
    """
    df_silver = df_bronze.copy()
    corrections_records = []

    for rule in rules:
        # Identify which performances this rule applies to
        perf_ids = identify_performances(df_silver, rule.applies_to)

        for perf_id in perf_ids:
            for correction in rule.corrections:
                # Get old value before change
                old_value = df_silver.loc[
                    df_silver["perf_id"] == perf_id, correction.field
                ].iloc[0]

                # Apply correction
                new_value = apply_correction(df_silver, perf_id, correction)

                # Update dataframe
                df_silver.loc[
                    df_silver["perf_id"] == perf_id, correction.field
                ] = new_value

                # Track change
                if track_changes:
                    record = CorrectionRecord(
                        rule_id=rule.rule_id,
                        perf_id=perf_id,
                        field=correction.field,
                        old_value=old_value,
                        new_value=new_value,
                        applied_date=datetime.now(),
                        reviewer=rule.metadata.get("reviewer", ""),
                        source_file=rule.metadata.get("source_file", ""),
                    )
                    corrections_records.append(record)

    # Convert corrections to dataframe
    if corrections_records:
        manifest_df = pd.DataFrame(
            [asdict(r) for r in corrections_records]
        )
    else:
        manifest_df = pd.DataFrame()

    return df_silver, manifest_df


def save_corrections_manifest(
    manifest_df: pd.DataFrame, output_path: Union[str, Path]
) -> None:
    """Save corrections manifest to parquet file.

    Args:
        manifest_df: Corrections manifest dataframe.
        output_path: Path to save parquet file.
    """
    if len(manifest_df) > 0:
        manifest_df.to_parquet(output_path, index=False)


def load_corrections_manifest(manifest_path: Union[str, Path]) -> pd.DataFrame:
    """Load corrections manifest from parquet file.

    Args:
        manifest_path: Path to manifest parquet file.

    Returns:
        Corrections manifest dataframe.
    """
    if Path(manifest_path).exists():
        return pd.read_parquet(manifest_path)
    return pd.DataFrame()


def report_transformations(manifest_df: pd.DataFrame) -> None:
    """Print a summary report of applied transformations.

    Args:
        manifest_df: Corrections manifest dataframe.
    """
    if len(manifest_df) == 0:
        print("No transformations applied.")
        return

    print("\n" + "=" * 70)
    print("SILVER LAYER TRANSFORMATIONS REPORT")
    print("=" * 70)

    print(f"\nTotal corrections: {len(manifest_df)}")
    print(f"Rules applied: {manifest_df['rule_id'].nunique()}")
    print(f"Performances affected: {manifest_df['perf_id'].nunique()}")
    print(f"Fields modified: {manifest_df['field'].nunique()}")

    print("\nBy Rule:")
    for rule_id in manifest_df["rule_id"].unique():
        rule_records = manifest_df[manifest_df["rule_id"] == rule_id]
        print(f"  {rule_id}: {len(rule_records)} corrections")
        for field in rule_records["field"].unique():
            field_count = len(rule_records[rule_records["field"] == field])
            print(f"    - {field}: {field_count} changes")

    print("\nReviewers:")
    for reviewer in manifest_df["reviewer"].unique():
        if reviewer:
            count = len(manifest_df[manifest_df["reviewer"] == reviewer])
            print(f"  {reviewer}: {count} corrections")

    print("\n" + "=" * 70 + "\n")


def verify_reproducibility(
    df_bronze: pd.DataFrame,
    rules: List[TransformationRule],
    df_silver_original: pd.DataFrame,
) -> bool:
    """Verify that transformations are reproducible.

    Applies the same rules again and verifies identical results.

    Args:
        df_bronze: Original bronze dataframe.
        rules: Transformation rules.
        df_silver_original: Original silver dataframe result.

    Returns:
        True if transformation is reproducible, False otherwise.
    """
    df_silver_recomputed, _ = apply_transformations(df_bronze, rules, track_changes=False)

    # Compare results
    try:
        pd.testing.assert_frame_equal(
            df_silver_original.reset_index(drop=True),
            df_silver_recomputed.reset_index(drop=True),
            check_dtype=True,
        )
        return True
    except AssertionError:
        return False
