Medallion Architecture: Bronze → Silver → Gold
==============================================

This guide explains the medallion data architecture pattern for organizing performance data across layers with full lineage and reproducibility.

What is Medallion Architecture?
-------------------------------

Medallion (or lakehouse) architecture organizes data into three layers:

- **Bronze** - Raw, unprocessed source data
- **Silver** - Cleaned, validated, feature-engineered data
- **Gold** - Aggregated, denormalized analytics-ready data

This pattern is industry standard in data engineering (used by Databricks, AWS, enterprises) and provides:

- **Auditability** - Source data preserved, nothing lost
- **Reproducibility** - Regenerate any layer from source
- **Flexibility** - Change processing without losing raw data
- **Performance** - Gold layer optimized for queries
- **Debugging** - Trace any result back to source

Bronze Layer: Raw Source Data
------------------------------

The bronze layer stores raw data as received from sources, minimally processed.

What Goes in Bronze
^^^^^^^^^^^^^^^^^^^

- Direct import from athle.fr (HTML parsed)
- CSV/Excel uploads (as-is, no cleaning)
- API responses (original schema)
- Any raw external data

Key Characteristics:

- **Immutable** - Never modified after creation
- **Complete** - All original columns preserved
- **Append-only** - New imports create new files, never overwrite
- **Source of truth** - Official version for auditing/compliance

Example: Save Raw Import
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from athletics_performance.medallion import PerformanceMedallion
    from athletics_performance.storage import LocalDataStore
    from athletics_performance.importers import AthleFrImporter

    store = LocalDataStore('/data/athletics')
    medallion = PerformanceMedallion(store)
    importer = AthleFrImporter(data_store=store)

    # Fetch raw data
    raw_df = importer.fetch_data(club_id="069106", season=2026)

    # Save to bronze (immutable)
    medallion.save_bronze(
        raw_df,
        'ac_lyon_april_2026'
    )

    # Later: verify the bronze data is unchanged
    verified = medallion.load_bronze('ac_lyon_april_2026')
    assert len(verified) == len(raw_df)  # No loss of data

Silver Layer: Processed & Feature-Engineered Data
--------------------------------------------------

The silver layer contains cleaned, validated data with computed features. It's still organized by the original data structure but with quality improvements.

What Goes in Silver
^^^^^^^^^^^^^^^^^^^

- **Deduplication** - Remove duplicate performance IDs
- **Type conversion** - String times → float, etc.
- **Data cleaning** - Handle missing values, fix formats
- **Feature engineering** - Add computed columns (scores, derived fields)
- **Validation** - Filter invalid/impossible values
- **Enrichment** - Join with reference data

Key Characteristics:

- **Reproducible** - Exact transformations documented
- **Regeneratable** - Can recreate from bronze anytime
- **Multi-version** - Different silver versions for different purposes OK
- **Traceable** - Can always see which transformation created it

Example: Process Pipeline (Bronze → Silver)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    import pandas as pd
    from athletics_performance.medallion import PerformanceMedallion

    medallion = PerformanceMedallion(store)

    # Define transformation pipeline
    transformations = [
        # Step 1: Deduplicate
        lambda df: df.drop_duplicates(subset=['perf_id']),

        # Step 2: Type conversion
        lambda df: df.assign(
            perf_float=pd.to_numeric(df['performance'], errors='coerce')
        ),

        # Step 3: Data cleaning
        lambda df: df[df['perf_float'].notna()],  # Remove invalid

        # Step 4: Feature engineering (World Athletics scores)
        lambda df: df.assign(
            wa_points=df.apply(
                lambda row: compute_world_athletics_score(
                    row['perf_float'],
                    row['event_name']
                ),
                axis=1
            )
        ),

        # Step 5: Further validation
        lambda df: df[df['wa_points'] > 0],
    ]

    # Execute pipeline
    processed = medallion.process_pipeline(
        bronze_name='ac_lyon_april_2026',
        silver_name='ac_lyon_april_2026_processed',
        transformations=transformations
    )

    print(f"Bronze: {bronze_rows} rows")
    print(f"Silver: {len(processed)} rows (after cleaning)")

Multiple Silver Versions
^^^^^^^^^^^^^^^^^^^^^^^^

Create different silver versions for different use cases:

.. code-block:: python

    # Version 1: Minimal processing
    medallion.process_pipeline(
        'ac_lyon_april_2026',
        'ac_lyon_april_minimal',
        [
            lambda df: df.drop_duplicates(subset=['perf_id']),
            lambda df: df.dropna(subset=['performance']),
        ]
    )

    # Version 2: Full scoring
    medallion.process_pipeline(
        'ac_lyon_april_2026',
        'ac_lyon_april_scored',
        [
            lambda df: df.drop_duplicates(subset=['perf_id']),
            lambda df: df.assign(
                perf_float=pd.to_numeric(df['performance'], errors='coerce')
            ),
            lambda df: df.assign(wa_points=df['perf_float'].apply(score_func)),
        ]
    )

    # Version 3: Regional aggregation
    medallion.process_pipeline(
        'ac_lyon_april_2026',
        'ac_lyon_april_regional',
        [
            lambda df: df.drop_duplicates(subset=['perf_id']),
            lambda df: df[df['region'] == 'ARA'],  # Filter to region
        ]
    )

Gold Layer: Analytics-Ready Aggregations
----------------------------------------

The gold layer contains aggregated, denormalized data optimized for visualization and analysis. One row typically represents one answer to a business question.

What Goes in Gold
^^^^^^^^^^^^^^^^^

- **Club records** (best time per event)
- **Athlete rankings** (top N athletes per event)
- **Trend data** (performance over time)
- **Dashboards** (pre-computed metrics)
- **ML features** (engineered features for models)

Key Characteristics:

- **Denormalized** - Joins already computed
- **Optimized** - Indexed for fast queries
- **Use-case driven** - Design around specific analysis needs
- **Multiple tables OK** - Different aggregations for different purposes

Example: Analytics Pipeline (Silver → Gold)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Create club records
    def club_records(df):
        """Best time per event."""
        return df.loc[df.groupby('event_name')['perf_float'].idxmin()]

    medallion.analytics_pipeline(
        silver_name='ac_lyon_april_2026_processed',
        gold_name='ac_lyon_records',
        aggregation_func=club_records
    )

Multiple Gold Datasets
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Gold Table 1: Club Records
    def get_records(df):
        """Best performance per event."""
        return df.loc[df.groupby('event_name')['perf_float'].idxmin()]

    medallion.analytics_pipeline(
        'ac_lyon_april_2026_processed',
        'ac_lyon_records',
        get_records
    )

    # Gold Table 2: Top Athletes
    def get_rankings(df):
        """Top 10 performances overall."""
        return df.nlargest(10, 'wa_points')[
            ['athlete_name', 'event_name', 'perf_float', 'wa_points', 'date']
        ]

    medallion.analytics_pipeline(
        'ac_lyon_april_2026_processed',
        'ac_lyon_rankings',
        get_rankings
    )

    # Gold Table 3: Monthly Trends
    def get_trends(df):
        """Average performance per month per event."""
        df = df.copy()
        df['month'] = df['date'].dt.to_period('M')
        return df.groupby(['month', 'event_name'])['perf_float'].agg([
            'mean', 'min', 'max', 'count'
        ]).reset_index()

    medallion.analytics_pipeline(
        'ac_lyon_april_2026_processed',
        'ac_lyon_trends',
        get_trends
    )

Complete End-to-End Example
---------------------------

.. code-block:: python

    import pandas as pd
    from athletics_performance.medallion import PerformanceMedallion
    from athletics_performance.storage import LocalDataStore
    from athletics_performance.importers import AthleFrImporter

    # Setup
    store = LocalDataStore('/data/athletics')
    medallion = PerformanceMedallion(store)
    importer = AthleFrImporter(data_store=store)

    # =========================
    # Phase 1: Import (Bronze)
    # =========================

    # Fetch and save raw data
    raw_df = importer.fetch_data(club_id="069106", season=2026)
    medallion.save_bronze(raw_df, 'ac_lyon_2026')

    # Verify bronze (immutable)
    bronze = medallion.load_bronze('ac_lyon_2026')
    print(f"Bronze layer: {len(bronze)} raw performances")

    # =========================
    # Phase 2: Process (Silver)
    # =========================

    def process_for_analysis(df):
        """Transform bronze to silver."""
        df = df.copy()

        # Deduplicate
        df = df.drop_duplicates(subset=['perf_id'])

        # Type conversions
        df['perf_float'] = pd.to_numeric(
            df['performance'],
            errors='coerce'
        )

        # Validation
        df = df[df['perf_float'].notna()]
        df = df[df['perf_float'] > 0]

        # Add features
        df['is_valid'] = df['perf_float'] > 0
        df['date'] = pd.to_datetime(df['date'])

        return df

    silver = medallion.process_pipeline(
        bronze_name='ac_lyon_2026',
        silver_name='ac_lyon_2026_processed',
        transformations=[process_for_analysis]
    )
    print(f"Silver layer: {len(silver)} processed performances")

    # =========================
    # Phase 3: Analytics (Gold)
    # =========================

    # Gold: Club Records
    def create_records(df):
        """Best time per event."""
        return df.loc[df.groupby('event_name')['perf_float'].idxmin()]

    records = medallion.analytics_pipeline(
        silver_name='ac_lyon_2026_processed',
        gold_name='ac_lyon_records',
        aggregation_func=create_records
    )
    print(f"Gold layer (records): {len(records)} events")

    # Gold: Performance Trends
    def create_trends(df):
        """Average per month per event."""
        df['month'] = df['date'].dt.to_period('M')
        return df.groupby(['month', 'event_name']).agg({
            'perf_float': ['mean', 'min', 'max', 'count']
        }).reset_index()

    trends = medallion.analytics_pipeline(
        silver_name='ac_lyon_2026_processed',
        gold_name='ac_lyon_trends',
        aggregation_func=create_trends
    )

    # =========================
    # Phase 4: Load for Analysis
    # =========================

    from athletics_performance import PerformanceCatalogue

    # Load gold and create catalogue
    records_df = medallion.load_gold('ac_lyon_records')
    catalogue = PerformanceCatalogue.from_dataframe(records_df)

    # Answer business questions
    event_100m = catalogue.filter(event_id="100m")
    record = event_100m.record()

    print(f"\n100m Club Record:")
    print(f"  Athlete: {record.athlete_name}")
    print(f"  Time: {record.result_value}s")
    print(f"  Date: {record.date}")

    # Trends analysis
    trends_df = medallion.load_gold('ac_lyon_trends')
    print(f"\nPerformance Trends: {len(trends_df)} month-event combinations")

Data Quality Checks
-------------------

At each layer, validate data quality:

.. code-block:: python

    def validate_bronze(df):
        """Verify bronze layer integrity."""
        assert df.duplicated('perf_id').sum() == 0, "Duplicates in bronze!"
        assert df['perf_id'].notna().all(), "Missing perf_ids!"
        return True

    def validate_silver(df):
        """Verify silver layer quality."""
        assert df.duplicated('perf_id').sum() == 0, "Duplicates in silver!"
        assert df['perf_float'].notna().all(), "NaN floats in silver!"
        assert (df['perf_float'] > 0).all(), "Invalid times in silver!"
        return True

    # Use in pipeline
    def process_with_validation(df):
        df = clean_and_score(df)
        assert validate_silver(df)
        return df

    medallion.process_pipeline(
        'ac_lyon_2026',
        'ac_lyon_2026_processed',
        [process_with_validation]
    )

Regenerating Layers
-------------------

Rebuild upper layers from lower ones without re-importing:

.. code-block:: python

    # Bugfix: Update scoring formula
    # Don't re-import from athle.fr, just regenerate from bronze

    def new_scoring_function(df):
        # Updated algorithm
        df['wa_points'] = df['perf_float'].apply(improved_score)
        return df

    # Regenerate silver with new scoring
    medallion.process_pipeline(
        'ac_lyon_2026',
        'ac_lyon_2026_processed_v2',
        [new_scoring_function],
        overwrite=True
    )

    # Regenerate gold from new silver
    medallion.analytics_pipeline(
        'ac_lyon_2026_processed_v2',
        'ac_lyon_records_v2',
        club_records,
        overwrite=True
    )

    # Old data intact for comparison
    old_records = medallion.load_gold('ac_lyon_records')
    new_records = medallion.load_gold('ac_lyon_records_v2')

Key Benefits
------------

✓ **Auditability** - Raw data preserved for compliance
✓ **Reproducibility** - Regenerate anytime from source
✓ **Flexibility** - Update processing without data loss
✓ **Performance** - Gold layer optimized for queries
✓ **Debugging** - Trace issues back to source
✓ **Documentation** - Layers show data pipeline clearly
✓ **Testing** - Test each transformation independently
✓ **Scaling** - Move to cloud easily (same code, different storage)

See Also
--------

- :doc:`guide_data_ingestion` - How to import data (Bronze)
- :doc:`guide_storage` - Storage configuration
- `Databricks Medallion Architecture <https://www.databricks.com/glossary/medallion-architecture>`_
- `AWS Data Lake Design <https://aws.amazon.com/solutions/datalake/>`_
