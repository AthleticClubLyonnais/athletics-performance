Silver Layer Transformations Guide
==================================

Overview
--------

The transformations system allows you to selectively correct specific performances during the bronze→silver conversion while maintaining full **reproducibility** and **auditability**. This guide covers the complete workflow for detecting and correcting data issues.

Key Principles
--------------

1. **Bronze Immutability**: Raw data in bronze layer is never modified
2. **Silver Corrections**: All corrections happen during bronze→silver transformation
3. **Declarative Rules**: Corrections are defined as YAML files (data artifacts), not code
4. **Full Audit Trail**: Every correction is tracked in a manifest with who, what, when, why
5. **Reproducibility**: Same bronze data + same rules = identical silver output, always
6. **Data Storage**: Rules and manifests stored alongside parquet files, not in git

Workflow
--------

The typical workflow has four steps:

1. **Detect**: Import data to bronze, validate for issues
2. **Define**: Create transformation rules in YAML
3. **Apply**: Apply rules during bronze→silver conversion
4. **Verify**: Check corrections and save audit trail

Step 1: Detect Issues
~~~~~~~~~~~~~~~~~~~~~

After importing raw data to bronze layer, validate event mappings to identify data quality issues:

.. code-block:: python

    from athletics_performance import apply_event_mapping, validate_event_mapping

    # Load bronze data
    df_bronze = pd.read_parquet("data/bronze/performances.parquet")

    # Validate event mapping
    report = validate_event_mapping(df_bronze)

    # Check for unrecognized events or data issues
    if report["unrecognized_rows"] > 0:
        print(f"Found {report['unrecognized_rows']} performances with issues")

Once you've identified problematic performances, you may discover additional data quality issues like:

- Incorrect dates (typos in year or month)
- Parsing errors in times or distances
- Wrong location codes
- Misclassified athletes
- Duplicate entries

Step 2: Define Transformation Rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a YAML file with transformation rules. Store this file **with your data**, not in git:

**Example: transformations_batch_20260425.yaml**

.. code-block:: yaml

    transformations:
      - rule_id: "fix_date_typo_p1"
        description: "Fix year typo in import batch - athlete had wrong year"
        applies_to:
          selector: "perf_ids"
          values: ["perf_001", "perf_002"]
        corrections:
          - field: "date"
            old_value: "2025-03-15"
            new_value: "2026-03-15"
        metadata:
          reviewer: "John Doe"
          source_file: "import_batch_20260425.csv"

      - rule_id: "fix_time_scaling"
        description: "Fix timing system error - values were 10x too large"
        applies_to:
          selector: "condition"
          match:
            - field: "location"
              equals: "Paris"
            - field: "result_value"
              gt: 50
        corrections:
          - field: "result_value"
            operation: "divide"
            operand: 10.0
        metadata:
          reviewer: "Jane Smith"
          source_file: "calibration_report.pdf"

Rule Selectors
~~~~~~~~~~~~~~

Two selector types are available:

**1. perf_ids Selector** - Target specific performances by ID:

.. code-block:: yaml

    applies_to:
      selector: "perf_ids"
      values: ["perf_001", "perf_003", "perf_005"]

**2. condition Selector** - Target performances matching criteria (AND logic):

.. code-block:: yaml

    applies_to:
      selector: "condition"
      match:
        - field: "event_id"
          equals: "100m"
        - field: "result_value"
          gt: 10.0

Supported condition operators:

- ``equals``: Exact match
- ``gt``: Greater than
- ``lt``: Less than
- ``gte``: Greater than or equal
- ``lte``: Less than or equal
- ``contains``: String contains (for text fields)

Correction Types
~~~~~~~~~~~~~~~~

**1. Simple Value Replacement**:

.. code-block:: yaml

    corrections:
      - field: "date"
        old_value: "2025-03-15"
        new_value: "2026-03-15"
        description: "Fixed typo in year"

**2. Mathematical Operations**:

.. code-block:: yaml

    corrections:
      - field: "result_value"
        operation: "divide"
        operand: 10.0
        description: "Divided by 10 to fix timing system error"

Supported operations: ``divide``, ``multiply``

**3. Multiple Corrections Per Rule**:

.. code-block:: yaml

    corrections:
      - field: "date"
        new_value: "2026-03-15"
      - field: "location"
        new_value: "London"

Step 3: Apply Transformations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Load your rules and apply them to bronze data:

.. code-block:: python

    from athletics_performance import (
        load_transformation_rules,
        apply_transformations,
        save_corrections_manifest,
    )
    import pandas as pd

    # Load bronze data
    df_bronze = pd.read_parquet("data/bronze/performances.parquet")

    # Load transformation rules from YAML
    with open("data/transformations_batch_20260425.yaml") as f:
        yaml_content = f.read()

    rules = load_transformation_rules(yaml_content)

    # Apply transformations
    df_silver, manifest = apply_transformations(df_bronze, rules)

    # Optionally save the manifest as audit trail
    save_corrections_manifest(manifest, "data/silver/corrections_manifest.parquet")

    # Save silver data
    df_silver.to_parquet("data/silver/performances.parquet")

Step 4: Verify Results
~~~~~~~~~~~~~~~~~~~~~~

Verify that transformations are reproducible and correct:

.. code-block:: python

    from athletics_performance import verify_reproducibility, report_transformations

    # Verify reproducibility
    if verify_reproducibility(df_bronze, rules, df_silver):
        print("✓ Transformations are reproducible!")
    else:
        print("✗ Transformation result differs on re-run - investigate!")

    # Print summary report
    report_transformations(manifest)

Sample Output::

    ======================================================================
    SILVER LAYER TRANSFORMATIONS REPORT
    ======================================================================

    Total corrections: 5
    Rules applied: 2
    Performances affected: 4
    Fields modified: 2

    By Rule:
      fix_date_typo_p1: 2 corrections
        - date: 2 changes
      fix_time_scaling: 3 corrections
        - result_value: 3 changes

    Reviewers:
      John Doe: 2 corrections
      Jane Smith: 3 corrections

    ======================================================================

Complete Workflow Example
-------------------------

Here's a complete example from raw data to silver layer with corrections:

.. code-block:: python

    import pandas as pd
    from athletics_performance import (
        load_transformation_rules,
        apply_transformations,
        save_corrections_manifest,
        verify_reproducibility,
        report_transformations,
        apply_event_mapping,
        validate_event_mapping,
    )

    # Step 1: Load bronze and validate
    df_bronze = pd.read_parquet("data/bronze/performances.parquet")
    mapping_report = validate_event_mapping(df_bronze)
    print(f"Event recognition: {mapping_report['recognition_rate']:.1f}%")

    # Step 2: Load transformation rules
    with open("data/transformations_batch_20260425.yaml") as f:
        rules = load_transformation_rules(f.read())

    print(f"Loaded {len(rules)} transformation rules")

    # Step 3: Apply transformations
    df_silver, manifest = apply_transformations(df_bronze, rules)

    # Step 4: Verify reproducibility
    assert verify_reproducibility(df_bronze, rules, df_silver), \
        "Transformation not reproducible!"

    # Step 5: Save results
    df_silver.to_parquet("data/silver/performances.parquet")
    save_corrections_manifest(manifest, "data/silver/corrections_manifest.parquet")

    # Step 6: Generate report
    report_transformations(manifest)

    print("\n✓ Silver layer created with full audit trail")

API Reference
-------------

Core Classes
~~~~~~~~~~~~

**Correction**
    A single field correction specification.

    Attributes:
        field (str): Field name to correct
        old_value (Any, optional): Expected old value (for validation)
        new_value (Any, optional): Replacement value
        operation (str, optional): Operation type ("divide", "multiply")
        operand (float, optional): Operation argument
        description (str, optional): Human-readable description

**TransformationRule**
    A complete transformation rule with metadata.

    Attributes:
        rule_id (str): Unique rule identifier
        description (str): Human-readable description
        applies_to (Dict): Selector specification (perf_ids or condition)
        corrections (List[Correction]): Corrections to apply
        metadata (Dict): Additional metadata (reviewer, source_file, etc.)

**CorrectionRecord**
    Audit record of a single applied correction.

    Attributes:
        rule_id (str): Rule that created this correction
        perf_id (str): Performance ID that was corrected
        field (str): Field that was modified
        old_value (Any): Value before correction
        new_value (Any): Value after correction
        applied_date (datetime): When correction was applied
        reviewer (str): Person who reviewed/approved the rule
        source_file (str): Source document (import file, report, etc.)

Core Functions
~~~~~~~~~~~~~~

**load_transformation_rules(yaml_content: str) → List[TransformationRule]**
    Load transformation rules from YAML content.

    Args:
        yaml_content: YAML string containing transformation rules

    Returns:
        List of TransformationRule objects

    Raises:
        ValueError: If YAML is invalid or missing required fields

**identify_performances(df, selector) → List[str]**
    Identify which performances match a selector.

    Supports two selector types:
    - "perf_ids": Simple list of specific performance IDs
    - "condition": Complex matching with field equals/gt/lt/gte/lte/contains

    Args:
        df: Performance dataframe
        selector: Selector specification from transformation rule

    Returns:
        List of perf_id values that match the selector

**apply_transformations(df_bronze, rules, track_changes=True) → (DataFrame, DataFrame)**
    Apply transformation rules to bronze data.

    Args:
        df_bronze: Bronze layer dataframe (not modified)
        rules: List of transformation rules to apply
        track_changes: Whether to track changes in manifest

    Returns:
        Tuple of (transformed_df, corrections_manifest)
        - transformed_df: Corrected silver layer dataframe
        - corrections_manifest: DataFrame with audit trail (empty if track_changes=False)

**save_corrections_manifest(manifest_df, output_path) → None**
    Save corrections manifest to parquet file.

    Args:
        manifest_df: Corrections manifest dataframe
        output_path: Path to save parquet file

**load_corrections_manifest(manifest_path) → DataFrame**
    Load corrections manifest from parquet file.

    Args:
        manifest_path: Path to manifest parquet file

    Returns:
        Corrections manifest dataframe (empty if file doesn't exist)

**verify_reproducibility(df_bronze, rules, df_silver_original) → bool**
    Verify that transformations are reproducible.

    Applies the same rules again and verifies identical results.

    Args:
        df_bronze: Original bronze dataframe
        rules: Transformation rules
        df_silver_original: Original silver dataframe result

    Returns:
        True if transformation is reproducible, False otherwise

**report_transformations(manifest_df) → None**
    Print a summary report of applied transformations.

    Args:
        manifest_df: Corrections manifest dataframe

Best Practices
--------------

1. **Document Every Rule**: Include clear descriptions and metadata in rules
2. **Review Before Applying**: Have another person review rules before applying to production data
3. **Verify Reproducibility**: Always call verify_reproducibility() before saving
4. **Keep Audit Trail**: Save the corrections manifest alongside silver data
5. **Version Your Rules**: Use timestamped filenames (e.g., transformations_batch_20260425.yaml)
6. **Test Small First**: Test rules on a subset before applying to all data
7. **Archive Source Documents**: Keep referenced PDFs, import logs, etc. for traceability

Storage Location
----------------

Transformation files are stored **alongside parquet files in your data store**:

.. code-block:: text

    data/
    ├── bronze/
    │   ├── performances.parquet
    │   └── transformations_batch_20260425.yaml
    ├── silver/
    │   ├── performances.parquet
    │   └── corrections_manifest.parquet
    └── gold/
        └── analytics.parquet

These files are NOT committed to git because they are data artifacts, not code.
Store them in your data warehouse or versioning system alongside the parquet files.

FAQ
---

**Q: Can I apply multiple rule sets to the same data?**
    A: Yes. Load all rules into a single list and pass them to apply_transformations().
    Rules are applied in order, so later rules can see corrections from earlier rules.

**Q: What if I need to correct an already-corrected value?**
    A: Create a new transformation YAML with updated rules. Since transformations are
    reproducible, you can always regenerate silver from bronze + all rules.

**Q: How do I undo a transformation?**
    A: Delete the corresponding rule(s) from the YAML file and regenerate silver from bronze.
    The audit trail (manifest) will show what was previously corrected.

**Q: Can transformations modify multiple fields for the same performance?**
    A: Yes. A single rule can have multiple corrections for different fields. Each field
    modification is tracked separately in the audit trail.

**Q: What data types are supported in corrections?**
    A: Any Python/Pandas type: strings, numbers, dates, booleans, etc. Operations
    (divide, multiply) work on numeric types.

See Also
--------

- :doc:`guide_event_registry` - Validating and mapping event names
- README.md - Package overview and quick start
- examples/ - Sample notebooks demonstrating workflows
