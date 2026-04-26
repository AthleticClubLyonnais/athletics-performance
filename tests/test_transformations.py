"""Tests for silver layer data transformations."""

import pytest
import pandas as pd
from datetime import datetime
from pathlib import Path
from athletics_performance.transformations import (
    Correction,
    TransformationRule,
    CorrectionRecord,
    load_transformation_rules,
    identify_performances,
    apply_correction,
    apply_transformations,
    save_corrections_manifest,
    load_corrections_manifest,
    verify_reproducibility,
)


class TestCorrectionDataclass:
    """Test Correction dataclass."""

    def test_correction_with_simple_replacement(self):
        """Correction can be created with old/new values."""
        corr = Correction(field="date", old_value="2025-03-15", new_value="2026-03-15")
        assert corr.field == "date"
        assert corr.old_value == "2025-03-15"
        assert corr.new_value == "2026-03-15"
        assert corr.operation is None

    def test_correction_with_operation(self):
        """Correction can be created with operation and operand."""
        corr = Correction(field="time", operation="divide", operand=10.0)
        assert corr.field == "time"
        assert corr.operation == "divide"
        assert corr.operand == 10.0

    def test_correction_with_description(self):
        """Correction can include description."""
        corr = Correction(
            field="date",
            old_value="2025-03-15",
            new_value="2026-03-15",
            description="Fixed year typo",
        )
        assert corr.description == "Fixed year typo"


class TestTransformationRuleDataclass:
    """Test TransformationRule dataclass."""

    def test_rule_creation(self):
        """TransformationRule can be created with required fields."""
        rule = TransformationRule(
            rule_id="fix_date_001",
            description="Fix date typo for athlete X",
            applies_to={"selector": "perf_ids", "values": ["perf_001"]},
        )
        assert rule.rule_id == "fix_date_001"
        assert rule.description == "Fix date typo for athlete X"
        assert rule.corrections == []

    def test_rule_with_corrections(self):
        """TransformationRule can include corrections."""
        corrections = [
            Correction(field="date", old_value="2025-03-15", new_value="2026-03-15")
        ]
        rule = TransformationRule(
            rule_id="fix_date_001",
            description="Fix date",
            applies_to={"selector": "perf_ids", "values": ["perf_001"]},
            corrections=corrections,
        )
        assert len(rule.corrections) == 1
        assert rule.corrections[0].field == "date"

    def test_rule_with_metadata(self):
        """TransformationRule can include metadata."""
        rule = TransformationRule(
            rule_id="fix_date_001",
            description="Fix date",
            applies_to={"selector": "perf_ids", "values": ["perf_001"]},
            metadata={"reviewer": "John Doe", "source_file": "import_batch_20260425.csv"},
        )
        assert rule.metadata["reviewer"] == "John Doe"
        assert rule.metadata["source_file"] == "import_batch_20260425.csv"


class TestLoadTransformationRules:
    """Test loading transformation rules from YAML."""

    def test_load_empty_yaml(self):
        """Load returns empty list for empty YAML."""
        yaml_content = ""
        rules = load_transformation_rules(yaml_content)
        assert rules == []

    def test_load_no_transformations_key(self):
        """Load returns empty list if 'transformations' key missing."""
        yaml_content = "some_other_key: value"
        rules = load_transformation_rules(yaml_content)
        assert rules == []

    def test_load_single_rule(self):
        """Load parses single transformation rule."""
        yaml_content = """
transformations:
  - rule_id: "fix_date"
    description: "Fix date error"
    applies_to:
      selector: "perf_ids"
      values: ["perf_001", "perf_002"]
    corrections:
      - field: "date"
        old_value: "2025-03-15"
        new_value: "2026-03-15"
"""
        rules = load_transformation_rules(yaml_content)
        assert len(rules) == 1
        assert rules[0].rule_id == "fix_date"
        assert rules[0].description == "Fix date error"
        assert len(rules[0].corrections) == 1

    def test_load_multiple_rules(self):
        """Load parses multiple rules."""
        yaml_content = """
transformations:
  - rule_id: "fix_date"
    description: "Fix date"
    applies_to:
      selector: "perf_ids"
      values: ["perf_001"]
    corrections:
      - field: "date"
        new_value: "2026-03-15"
  - rule_id: "fix_time"
    description: "Fix time"
    applies_to:
      selector: "perf_ids"
      values: ["perf_002"]
    corrections:
      - field: "result_value"
        operation: "divide"
        operand: 100
"""
        rules = load_transformation_rules(yaml_content)
        assert len(rules) == 2
        assert rules[0].rule_id == "fix_date"
        assert rules[1].rule_id == "fix_time"

    def test_load_with_metadata(self):
        """Load preserves metadata."""
        yaml_content = """
transformations:
  - rule_id: "fix_date"
    description: "Fix date"
    applies_to:
      selector: "perf_ids"
      values: ["perf_001"]
    metadata:
      reviewer: "John Doe"
      source_file: "import_batch.csv"
    corrections:
      - field: "date"
        new_value: "2026-03-15"
"""
        rules = load_transformation_rules(yaml_content)
        assert rules[0].metadata["reviewer"] == "John Doe"
        assert rules[0].metadata["source_file"] == "import_batch.csv"

    def test_load_invalid_yaml(self):
        """Load raises ValueError for invalid YAML."""
        yaml_content = "{ invalid yaml :"
        with pytest.raises(ValueError, match="Invalid YAML"):
            load_transformation_rules(yaml_content)


class TestIdentifyPerformances:
    """Test performance selection by various criteria."""

    @pytest.fixture
    def sample_df(self):
        """Create sample dataframe."""
        return pd.DataFrame({
            "perf_id": ["p1", "p2", "p3", "p4", "p5"],
            "athlete_id": ["a1", "a2", "a1", "a3", "a1"],
            "event_id": ["100m", "long_jump", "100m", "high_jump", "100m"],
            "result_value": [10.5, 6.8, 10.2, 1.9, 10.1],
            "location": ["Paris", "London", "Paris", "Paris", "Berlin"],
        })

    def test_identify_by_perf_ids(self, sample_df):
        """Identify performances by explicit perf_id list."""
        selector = {"selector": "perf_ids", "values": ["p1", "p3"]}
        perf_ids = identify_performances(sample_df, selector)
        assert set(perf_ids) == {"p1", "p3"}

    def test_identify_by_perf_ids_missing_values(self, sample_df):
        """Identify only returns perf_ids that exist in dataframe."""
        selector = {"selector": "perf_ids", "values": ["p1", "p99", "p5"]}
        perf_ids = identify_performances(sample_df, selector)
        assert set(perf_ids) == {"p1", "p5"}

    def test_identify_by_condition_equals(self, sample_df):
        """Identify by condition with equals operator."""
        selector = {
            "selector": "condition",
            "match": [{"field": "event_id", "equals": "100m"}],
        }
        perf_ids = identify_performances(sample_df, selector)
        assert set(perf_ids) == {"p1", "p3", "p5"}

    def test_identify_by_condition_gt(self, sample_df):
        """Identify by condition with greater-than operator."""
        selector = {
            "selector": "condition",
            "match": [{"field": "result_value", "gt": 6.5}],
        }
        perf_ids = identify_performances(sample_df, selector)
        assert set(perf_ids) == {"p1", "p2", "p3", "p5"}

    def test_identify_by_condition_lt(self, sample_df):
        """Identify by condition with less-than operator."""
        selector = {
            "selector": "condition",
            "match": [{"field": "result_value", "lt": 2.0}],
        }
        perf_ids = identify_performances(sample_df, selector)
        assert set(perf_ids) == {"p4"}

    def test_identify_by_condition_contains(self, sample_df):
        """Identify by condition with string contains."""
        selector = {
            "selector": "condition",
            "match": [{"field": "location", "contains": "Par"}],
        }
        perf_ids = identify_performances(sample_df, selector)
        assert set(perf_ids) == {"p1", "p3", "p4"}

    def test_identify_by_multiple_conditions(self, sample_df):
        """Identify by multiple conditions (AND logic)."""
        selector = {
            "selector": "condition",
            "match": [
                {"field": "event_id", "equals": "100m"},
                {"field": "result_value", "lt": 10.3},
            ],
        }
        perf_ids = identify_performances(sample_df, selector)
        assert set(perf_ids) == {"p3", "p5"}

    def test_identify_unknown_selector_type(self, sample_df):
        """Identify returns empty list for unknown selector type."""
        selector = {"selector": "unknown_type", "values": []}
        perf_ids = identify_performances(sample_df, selector)
        assert perf_ids == []


class TestApplyCorrection:
    """Test applying single corrections."""

    @pytest.fixture
    def sample_df(self):
        """Create sample dataframe."""
        return pd.DataFrame({
            "perf_id": ["p1", "p2", "p3"],
            "date": ["2025-03-15", "2025-06-20", "2025-12-01"],
            "result_value": [10.5, 20.0, 100.0],
        })

    def test_apply_simple_replacement(self, sample_df):
        """Apply correction with new_value."""
        corr = Correction(field="date", new_value="2026-03-15")
        new_value = apply_correction(sample_df, "p1", corr)
        assert new_value == "2026-03-15"

    def test_apply_divide_operation(self, sample_df):
        """Apply correction with divide operation."""
        corr = Correction(field="result_value", operation="divide", operand=10.0)
        new_value = apply_correction(sample_df, "p1", corr)
        assert new_value == 1.05

    def test_apply_multiply_operation(self, sample_df):
        """Apply correction with multiply operation."""
        corr = Correction(field="result_value", operation="multiply", operand=2.0)
        new_value = apply_correction(sample_df, "p2", corr)
        assert new_value == 40.0

    def test_apply_to_nonexistent_perf(self, sample_df):
        """Apply correction to nonexistent perf_id returns None."""
        corr = Correction(field="date", new_value="2026-03-15")
        new_value = apply_correction(sample_df, "p99", corr)
        assert new_value is None


class TestApplyTransformations:
    """Test applying all transformation rules."""

    @pytest.fixture
    def sample_df(self):
        """Create sample dataframe."""
        return pd.DataFrame({
            "perf_id": ["p1", "p2", "p3"],
            "athlete_id": ["a1", "a2", "a1"],
            "date": ["2025-03-15", "2025-06-20", "2025-12-01"],
            "result_value": [10.5, 20.0, 100.0],
            "location": ["Paris", "Paris", "Berlin"],
        })

    def test_apply_no_rules(self, sample_df):
        """Apply with no rules returns unchanged dataframe."""
        df_silver, manifest = apply_transformations(sample_df, [])
        pd.testing.assert_frame_equal(df_silver, sample_df)
        assert len(manifest) == 0

    def test_apply_single_rule(self, sample_df):
        """Apply single rule to single performance."""
        rule = TransformationRule(
            rule_id="fix_date",
            description="Fix date typo",
            applies_to={"selector": "perf_ids", "values": ["p1"]},
            corrections=[
                Correction(field="date", old_value="2025-03-15", new_value="2026-03-15")
            ],
            metadata={"reviewer": "John Doe"},
        )
        df_silver, manifest = apply_transformations(sample_df, [rule])

        assert df_silver.loc[df_silver["perf_id"] == "p1", "date"].iloc[0] == "2026-03-15"
        assert df_silver.loc[df_silver["perf_id"] == "p2", "date"].iloc[0] == "2025-06-20"
        assert len(manifest) == 1
        assert manifest.iloc[0]["rule_id"] == "fix_date"
        assert manifest.iloc[0]["perf_id"] == "p1"
        assert manifest.iloc[0]["old_value"] == "2025-03-15"
        assert manifest.iloc[0]["new_value"] == "2026-03-15"

    def test_apply_multiple_rules(self, sample_df):
        """Apply multiple rules sequentially."""
        rules = [
            TransformationRule(
                rule_id="fix_date",
                description="Fix date",
                applies_to={"selector": "perf_ids", "values": ["p1"]},
                corrections=[Correction(field="date", new_value="2026-03-15")],
            ),
            TransformationRule(
                rule_id="fix_location",
                description="Fix location",
                applies_to={"selector": "perf_ids", "values": ["p2"]},
                corrections=[Correction(field="location", new_value="London")],
            ),
        ]
        df_silver, manifest = apply_transformations(sample_df, rules)

        assert df_silver.loc[df_silver["perf_id"] == "p1", "date"].iloc[0] == "2026-03-15"
        assert df_silver.loc[df_silver["perf_id"] == "p2", "location"].iloc[0] == "London"
        assert len(manifest) == 2

    def test_apply_rule_with_condition(self, sample_df):
        """Apply rule using condition selector."""
        rule = TransformationRule(
            rule_id="fix_high_results",
            description="Fix high result values",
            applies_to={
                "selector": "condition",
                "match": [{"field": "result_value", "gt": 50}],
            },
            corrections=[Correction(field="result_value", operation="divide", operand=10.0)],
        )
        df_silver, manifest = apply_transformations(sample_df, [rule])

        assert df_silver.loc[df_silver["perf_id"] == "p3", "result_value"].iloc[0] == 10.0
        assert df_silver.loc[df_silver["perf_id"] == "p1", "result_value"].iloc[0] == 10.5
        assert len(manifest) == 1

    def test_apply_multiple_corrections_per_rule(self, sample_df):
        """Apply rule with multiple corrections."""
        rule = TransformationRule(
            rule_id="fix_multiple",
            description="Fix multiple fields",
            applies_to={"selector": "perf_ids", "values": ["p1"]},
            corrections=[
                Correction(field="date", new_value="2026-03-15"),
                Correction(field="location", new_value="London"),
            ],
        )
        df_silver, manifest = apply_transformations(sample_df, [rule])

        assert df_silver.loc[df_silver["perf_id"] == "p1", "date"].iloc[0] == "2026-03-15"
        assert df_silver.loc[df_silver["perf_id"] == "p1", "location"].iloc[0] == "London"
        assert len(manifest) == 2

    def test_apply_no_tracking(self, sample_df):
        """Apply with track_changes=False doesn't create manifest."""
        rule = TransformationRule(
            rule_id="fix_date",
            description="Fix date",
            applies_to={"selector": "perf_ids", "values": ["p1"]},
            corrections=[Correction(field="date", new_value="2026-03-15")],
        )
        df_silver, manifest = apply_transformations(sample_df, [rule], track_changes=False)

        assert df_silver.loc[df_silver["perf_id"] == "p1", "date"].iloc[0] == "2026-03-15"
        assert len(manifest) == 0

    def test_apply_preserves_bronze(self, sample_df):
        """Apply doesn't modify original dataframe."""
        df_bronze_copy = sample_df.copy()
        rule = TransformationRule(
            rule_id="fix_date",
            description="Fix date",
            applies_to={"selector": "perf_ids", "values": ["p1"]},
            corrections=[Correction(field="date", new_value="2026-03-15")],
        )
        apply_transformations(sample_df, [rule])

        pd.testing.assert_frame_equal(sample_df, df_bronze_copy)


class TestCorrectionManifest:
    """Test saving and loading corrections manifest."""

    @pytest.fixture
    def sample_manifest(self):
        """Create sample manifest dataframe."""
        return pd.DataFrame([
            {
                "rule_id": "fix_date",
                "perf_id": "p1",
                "field": "date",
                "old_value": "2025-03-15",
                "new_value": "2026-03-15",
                "applied_date": datetime.now(),
                "reviewer": "John Doe",
                "source_file": "import_batch.csv",
            },
            {
                "rule_id": "fix_location",
                "perf_id": "p2",
                "field": "location",
                "old_value": "Paris",
                "new_value": "London",
                "applied_date": datetime.now(),
                "reviewer": "Jane Smith",
                "source_file": "corrections.yaml",
            },
        ])

    def test_save_manifest(self, sample_manifest, tmp_path):
        """Save manifest to parquet file."""
        output_path = tmp_path / "manifest.parquet"
        save_corrections_manifest(sample_manifest, output_path)

        assert output_path.exists()

    def test_load_manifest(self, sample_manifest, tmp_path):
        """Load manifest from parquet file."""
        output_path = tmp_path / "manifest.parquet"
        save_corrections_manifest(sample_manifest, output_path)
        loaded = load_corrections_manifest(output_path)

        assert len(loaded) == 2
        assert loaded.iloc[0]["rule_id"] == "fix_date"
        assert loaded.iloc[1]["rule_id"] == "fix_location"

    def test_load_nonexistent_manifest(self, tmp_path):
        """Load from nonexistent path returns empty dataframe."""
        manifest = load_corrections_manifest(tmp_path / "nonexistent.parquet")
        assert len(manifest) == 0

    def test_save_empty_manifest(self, tmp_path):
        """Save empty manifest doesn't create file."""
        output_path = tmp_path / "manifest.parquet"
        empty_manifest = pd.DataFrame()
        save_corrections_manifest(empty_manifest, output_path)

        assert not output_path.exists()


class TestReproducibility:
    """Test reproducibility verification."""

    @pytest.fixture
    def sample_df(self):
        """Create sample dataframe."""
        return pd.DataFrame({
            "perf_id": ["p1", "p2", "p3"],
            "date": ["2025-03-15", "2025-06-20", "2025-12-01"],
            "result_value": [10.5, 20.0, 100.0],
        })

    def test_verify_reproducible(self, sample_df):
        """Verify reproducibility when rules produce same result."""
        rule = TransformationRule(
            rule_id="fix_date",
            description="Fix date",
            applies_to={"selector": "perf_ids", "values": ["p1"]},
            corrections=[Correction(field="date", new_value="2026-03-15")],
        )
        rules = [rule]

        # Apply once to get original result
        df_silver_1, _ = apply_transformations(sample_df, rules)

        # Apply again to verify reproducibility
        is_reproducible = verify_reproducibility(sample_df, rules, df_silver_1)

        assert is_reproducible is True

    def test_verify_not_reproducible_different_result(self, sample_df):
        """Verify reproducibility fails when results differ."""
        rule = TransformationRule(
            rule_id="fix_date",
            description="Fix date",
            applies_to={"selector": "perf_ids", "values": ["p1"]},
            corrections=[Correction(field="date", new_value="2026-03-15")],
        )
        rules = [rule]

        # Create a modified silver dataframe
        df_silver_wrong = sample_df.copy()
        df_silver_wrong.loc[df_silver_wrong["perf_id"] == "p2", "result_value"] = 999.0

        # Verify should fail
        is_reproducible = verify_reproducibility(sample_df, rules, df_silver_wrong)

        assert is_reproducible is False


class TestIntegration:
    """Integration tests for complete workflow."""

    def test_workflow_detect_and_correct(self, tmp_path):
        """Complete workflow: detect issues and apply corrections."""
        # Bronze data with errors (all numeric data for consistency)
        df_bronze = pd.DataFrame({
            "perf_id": ["p1", "p2", "p3"],
            "athlete_id": ["a1", "a2", "a1"],
            "location_code": [1, 2, 3],  # numeric location codes
            "result_value": [10.5, 20.0, 100.0],
            "score": [100, 200, 300],
        })

        # Create transformation rules
        rules = [
            TransformationRule(
                rule_id="fix_location_p1",
                description="Fix location code for p1",
                applies_to={"selector": "perf_ids", "values": ["p1"]},
                corrections=[Correction(field="location_code", old_value=1, new_value=2)],
                metadata={"reviewer": "John Doe"},
            ),
            TransformationRule(
                rule_id="fix_result_p3",
                description="Fix decimal in result",
                applies_to={"selector": "perf_ids", "values": ["p3"]},
                corrections=[Correction(field="result_value", operation="divide", operand=10.0)],
                metadata={"reviewer": "Jane Smith"},
            ),
        ]

        # Apply transformations
        df_silver, manifest = apply_transformations(df_bronze, rules)

        # Convert manifest values to strings for parquet storage
        if len(manifest) > 0:
            manifest["old_value"] = manifest["old_value"].astype(str)
            manifest["new_value"] = manifest["new_value"].astype(str)

        # Save manifest
        manifest_path = tmp_path / "manifest.parquet"
        save_corrections_manifest(manifest, manifest_path)

        # Verify corrections
        assert df_silver.loc[df_silver["perf_id"] == "p1", "location_code"].iloc[0] == 2
        assert df_silver.loc[df_silver["perf_id"] == "p3", "result_value"].iloc[0] == 10.0

        # Verify manifest saved
        assert manifest_path.exists()
        loaded_manifest = load_corrections_manifest(manifest_path)
        assert len(loaded_manifest) == 2

        # Verify reproducibility
        assert verify_reproducibility(df_bronze, rules, df_silver) is True

    def test_workflow_yaml_rules(self, tmp_path):
        """Complete workflow using YAML rules."""
        # Create YAML rules file
        yaml_content = """
transformations:
  - rule_id: "fix_date_batch"
    description: "Fix batch import date errors"
    applies_to:
      selector: "condition"
      match:
        - field: "location"
          equals: "Paris"
    corrections:
      - field: "date"
        operation: "replace"
        new_value: "2026-01-01"
    metadata:
      reviewer: "Data Admin"
      source_file: "batch_import_20260425.csv"
"""
        # Load rules from YAML
        rules = load_transformation_rules(yaml_content)

        # Apply to sample data
        df_bronze = pd.DataFrame({
            "perf_id": ["p1", "p2", "p3"],
            "date": ["2025-06-20", "2025-06-20", "2025-12-01"],
            "location": ["Paris", "London", "Paris"],
        })

        df_silver, manifest = apply_transformations(df_bronze, rules)

        # Verify corrections applied to Paris locations
        assert df_silver.loc[df_silver["perf_id"] == "p1", "date"].iloc[0] == "2026-01-01"
        assert df_silver.loc[df_silver["perf_id"] == "p2", "date"].iloc[0] == "2025-06-20"
        assert df_silver.loc[df_silver["perf_id"] == "p3", "date"].iloc[0] == "2026-01-01"
        assert len(manifest) == 2
