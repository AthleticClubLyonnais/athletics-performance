Data Ingestion: Importing Performances
=======================================

This guide explains how to import athletic performance data into the library, handling duplicates, and processing the data for analysis.

Overview
--------

The library provides an extensible framework for importing performance data from various sources:

- **athle.fr** - French athletics federation website (web scraping)
- **Custom sources** - CSV, Excel, APIs (implement ``PerformanceImporter``)

Basic Concepts
--------------

Performance Importer
^^^^^^^^^^^^^^^^^^^^

An importer handles three main operations:

1. **Fetch** - Retrieve raw data from source (web scraping, file reading, API call)
2. **Parse** - Transform raw data to standardized format (column mapping, type conversion)
3. **Store** - Save to Parquet for efficient storage and retrieval

.. code-block:: python

    from athletics_performance.importers import AthleFrImporter

    importer = AthleFrImporter()

    # Fetch raw HTML from athle.fr
    raw_data = importer.fetch_data(club_id="069106", season=2026)

    # Parse to standard format
    parsed = importer.parse_performances(raw_data)

    # Or do it all at once
    importer.import_to_parquet(club_id="069106", season=2026)

Importing from athle.fr
-----------------------

The French Athletics Federation (Fédération Française d'Athlétisme) publishes club performance results at athle.fr. The ``AthleFrImporter`` fetches these results using web scraping.

Basic Import
^^^^^^^^^^^^

.. code-block:: python

    from athletics_performance.importers import AthleFrImporter
    from athletics_performance.storage import LocalDataStore

    # Create importer with default storage
    importer = AthleFrImporter()

    # Import performances for AC Lyon (club ID: 069106)
    output_path = importer.import_to_parquet(
        club_id="069106",
        season=2026
    )

    print(f"Data saved to: {output_path}")

The resulting Parquet file contains columns:

- ``perf_id`` - Unique performance identifier
- ``athlete_id`` - Athlete licence number
- ``athlete_name`` - Athlete full name
- ``event_name`` - Event (e.g., "100m", "Longueur")
- ``performance`` - Result as string (time or distance)
- ``date`` - Competition date
- ``venue`` - Competition location
- ``club_name`` - Athlete's club
- ``measurement`` - "time" or "distance"
- ``unit`` - "s" (seconds) or "m" (meters)

Multiple Imports with Duplicate Handling
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When importing multiple times, you may get duplicate performances. Four strategies are available:

**Skip** (default) - Keep existing, ignore new duplicates:

.. code-block:: python

    importer.import_to_parquet(
        club_id="069106",
        handle_duplicates="skip"
    )
    # If already imported, new duplicates are ignored

**Replace** - Overwrite existing with new data:

.. code-block:: python

    importer.import_to_parquet(
        club_id="069106",
        handle_duplicates="replace"
    )
    # Updated performances replace old versions

**Error** - Raise error if duplicates found:

.. code-block:: python

    try:
        importer.import_to_parquet(
            club_id="069106",
            handle_duplicates="error"
        )
    except ValueError as e:
        print(f"Duplicates found: {e}")

**Keep** - Allow all duplicates:

.. code-block:: python

    importer.import_to_parquet(
        club_id="069106",
        handle_duplicates="keep"
    )
    # All performances kept, even duplicates

Detecting and Removing Duplicates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Check for duplicates in existing data:

.. code-block:: python

    # Find duplicate performance IDs
    duplicates = importer.get_duplicates("ac_lyon_2026.parquet")

    if len(duplicates) > 0:
        print(f"Found {len(duplicates)} duplicate records")
        print(duplicates[['athlete_name', 'event_name', 'date']])

Remove duplicates (keep first occurrence):

.. code-block:: python

    # Deduplicate (keep first occurrence)
    importer.deduplicate("ac_lyon_2026.parquet", keep="first")

    # Or keep last occurrence
    importer.deduplicate("ac_lyon_2026.parquet", keep="last")

Adding Computed Features
------------------------

After importing, add computed columns (scores, features) using transformations:

Simple Scoring
^^^^^^^^^^^^^^

.. code-block:: python

    def add_simple_scores(df):
        """Add points based on performance (higher is better)."""
        df = df.copy()
        perf_float = pd.to_numeric(df['performance'], errors='coerce')
        # Simple formula: 1000 - (performance * 10)
        df['score'] = (1000 - (perf_float * 10)).astype(int)
        return df

    importer.apply_transformation(
        "ac_lyon_2026.parquet",
        add_simple_scores,
        "ac_lyon_2026_scored.parquet"
    )

World Athletics Points
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from athletics_performance.scoring_tables import ScoringTableResolver

    def add_world_athletics_scores(df):
        """Compute official World Athletics points."""
        resolver = ScoringTableResolver()
        df = df.copy()

        scores = []
        for _, row in df.iterrows():
            try:
                # Get performance as float
                perf = float(row['performance'])

                # Lookup World Athletics points
                # (Note: requires athlete age category)
                points = 0  # Placeholder
                scores.append(points)
            except:
                scores.append(0)

        df['world_athletics_points'] = scores
        return df

    importer.apply_transformation(
        "ac_lyon_2026.parquet",
        add_world_athletics_scores,
        "ac_lyon_2026_scored.parquet"
    )

Custom Transformations
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    def clean_and_enrich(df):
        """Example: Clean data and add multiple features."""
        df = df.copy()

        # Convert performance to numeric
        df['perf_float'] = pd.to_numeric(
            df['performance'],
            errors='coerce'
        )

        # Filter valid performances
        df = df[df['perf_float'].notna()]

        # Add derived columns
        df['is_indoor'] = df['venue'].str.contains(
            'indoor|intérieur',
            case=False,
            na=False
        )

        return df

    importer.apply_transformation(
        "raw_data.parquet",
        clean_and_enrich,
        "cleaned_data.parquet"
    )

Complete Workflow Example
-------------------------

.. code-block:: python

    from athletics_performance.importers import AthleFrImporter
    from athletics_performance.storage import LocalDataStore
    from athletics_performance.medallion import PerformanceMedallion
    import pandas as pd

    # 1. Setup storage
    store = LocalDataStore('/data/athletics')
    importer = AthleFrImporter(data_store=store)
    medallion = PerformanceMedallion(store)

    # 2. Import (Bronze layer)
    importer.import_to_parquet(
        club_id="069106",
        season=2026,
        handle_duplicates="skip",
        output_file="ac_lyon_2026_raw.parquet"
    )
    medallion.save_bronze(
        importer.load_from_parquet("ac_lyon_2026_raw.parquet"),
        "ac_lyon_2026"
    )

    # 3. Process (Silver layer)
    def process_performances(df):
        """Clean and score performances."""
        df = df.copy()

        # Deduplicate
        df = df.drop_duplicates(subset=['perf_id'])

        # Convert to numeric
        df['perf_float'] = pd.to_numeric(
            df['performance'],
            errors='coerce'
        )

        # Add simple score
        df['score'] = (1000 - (df['perf_float'] * 10)).astype(int)

        # Keep valid only
        df = df[df['score'].notna()]

        return df

    medallion.process_pipeline(
        "ac_lyon_2026",
        "ac_lyon_2026_processed",
        [process_performances]
    )

    # 4. Analytics (Gold layer)
    def club_records(df):
        """Best time per event."""
        return df.loc[df.groupby('event_name')['perf_float'].idxmin()]

    medallion.analytics_pipeline(
        "ac_lyon_2026_processed",
        "ac_lyon_records",
        club_records
    )

    # 5. Load for analysis
    records = medallion.load_gold("ac_lyon_records")
    catalogue = PerformanceCatalogue.from_dataframe(records)

    # Find personal records
    for athlete_id in records['athlete_id'].unique():
        best = catalogue.filter(athlete_id=athlete_id).record()
        if best:
            print(f"{best.athlete_name}: {best.result_value}s in {best.event_id}")

See Also
--------

- :doc:`guide_storage` - Configuring where data is stored
- :doc:`guide_medallion` - Medallion architecture (bronze/silver/gold)
- :doc:`architecture` - System architecture overview
