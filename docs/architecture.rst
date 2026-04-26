System Architecture
====================

This document provides an overview of the athletics-performance library architecture, covering the data model, ingestion pipeline, storage, and analysis layers.

High-Level Architecture
-----------------------

.. code-block:: text

    ┌─────────────────────────────────────────────────────────────┐
    │                     External Sources                         │
    │  (athle.fr, CSV, API, etc.)                                 │
    └────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              Performance Importers                           │
    │  (AthleFrImporter, CSVImporter, etc.)                       │
    │  - Fetch: Retrieve raw data                                │
    │  - Parse: Transform to standard format                     │
    │  - Store: Save to Parquet files                            │
    └────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
    ┌─────────────────────────────────────────────────────────────┐
    │          Flexible Storage Backend                           │
    │  (Local Filesystem or AWS S3)                              │
    │  - Configuration via code, env vars, or config file       │
    │  - Supports both single-user and enterprise scale         │
    └────────────┬────────────────────────────────────────────────┘
                 │
    ┌────────────┴────────────────────────────────────────────────┐
    │                                                               │
    ▼                      ▼                      ▼                 │
┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  Bronze  │  │  Silver  │  │   Gold   │  Medallion Architecture  │
│  (Raw)   │  │(Processed)│  │(Analytics)        │
│          │  │          │  │          │        │
│ Immutable│  │Computed  │  │Aggregated│        │
│ Source   │  │Features  │  │ Prepared │        │
│  Truth   │  │          │  │          │        │
└────┬─────┘  └────┬─────┘  └────┬─────┘        │
     │             │             │              │
     │ (Transform) │ (Aggregate) │              │
     └─────────────┴─────────────┘              │
                 │                              │
                 ▼                              │
     ┌──────────────────────────┐               │
     │  PerformanceCatalogue    │◄──────────────┘
     │  - Filter & Query        │
     │  - Statistics            │
     │  - Ranking               │
     └────────┬─────────────────┘
              │
              ▼
    ┌─────────────────────────┐
    │   Analysis & Reporting  │
    │  - Dashboards           │
    │  - Machine Learning     │
    │  - Data Science         │
    └─────────────────────────┘

Core Components
---------------

Data Models
^^^^^^^^^^^

**Athlete**
  - Immutable record of athlete details
  - Automatic age category computation
  - License number as primary key

**Club**
  - Club information with auto-derived league codes
  - Department-to-league mapping
  - Club ID as primary key

**Event**
  - Event definition (100m, Long Jump, Marathon, etc.)
  - Measurement type (time or distance)
  - Pre-configured EVENT_CATALOG

**Performance**
  - Single recorded athletic result
  - References athlete, event, date, result
  - Automatic year-of-season (YOS) computation
  - Optionally references club, category at time of performance

**ClubMembership**
  - Track athlete club membership over time
  - Start/end dates for historical tracking
  - Active/inactive status computation

Performance Importers
^^^^^^^^^^^^^^^^^^^^^

Extensible framework for importing performances from various sources:

**PerformanceImporter** (Abstract Base Class)
  - ``fetch_data()`` - Retrieve raw data from source
  - ``parse_performances()`` - Transform to standard format
  - ``import_to_parquet()`` - Save to Parquet
  - ``apply_transformation()`` - Add computed columns
  - ``deduplicate()`` / ``get_duplicates()`` - Manage duplicates

**AthleFrImporter** (Concrete)
  - Scrapes athle.fr French athletics federation website
  - Maps French column names to English standard
  - Parses dates from DD/MM/YYYY format
  - Generates unique performance IDs

Storage Layer
^^^^^^^^^^^^^

**DataStore** (Abstract Interface)
  - ``exists(path)`` - Check if file exists
  - ``read_parquet(path)`` - Load Parquet file
  - ``write_parquet(df, path)`` - Save Parquet file
  - ``list_files(dir)`` - List directory contents
  - ``delete(path)`` - Remove file

**LocalDataStore** (Concrete)
  - Local filesystem backend
  - Default: ``~/.athletics_performance/data/``
  - Configurable path

**S3DataStore** (Concrete)
  - AWS S3 backend for cloud deployments
  - Supports arbitrary bucket/prefix
  - Uses boto3 (optional dependency)
  - IAM role or credential-based authentication

Configuration
  - **Code**: Pass ``DataStore`` to importer
  - **Environment**: ``ATHLETICS_STORAGE_TYPE``, ``ATHLETICS_STORAGE_PATH``, ``ATHLETICS_S3_*``
  - **Factory**: ``get_default_data_store(config_dict)``

Medallion Architecture
^^^^^^^^^^^^^^^^^^^^^^

**PerformanceMedallion** - Manages three data layers:

**Bronze Layer**
  - Raw data from importers
  - Immutable, append-only
  - All original columns preserved
  - Source of truth for auditing

**Silver Layer**
  - Cleaned, validated, deduplicated data
  - Added computed features (scores, derived columns)
  - Multiple versions for different purposes OK
  - Regeneratable from bronze

**Gold Layer**
  - Aggregated, denormalized analytics data
  - Pre-computed metrics for dashboards
  - Use-case driven (records, rankings, trends, etc.)
  - Optimized for queries

Scoring System
^^^^^^^^^^^^^^

**ScoringTables** (Abstract Base Class)
  - ``score(performance)`` - Compute points for result
  - ``performance_for_points(points)`` - Inverse lookup
  - ``available_events()`` - List scored events
  - ``applicable_categories`` - Age categories supported

**WorldAthletics2025ScoringTable** (Concrete)
  - Official World Athletics scoring tables
  - Parses 846-page PDF (70k+ rows)
  - Supports time conversion (seconds ↔ milliseconds)
  - Covers 100+ events and age categories

**BEYouthScoringTable** (Concrete)
  - French BE (12-13 years) category
  - Male and female tables unified
  - 16 track & field events

**MIYouthScoringTable** (Concrete)
  - French MI (14-15 years) category
  - Male and female tables unified
  - 21 track & field events

**ScoringTableResolver** (Factory)
  - Registry pattern for scoring tables
  - ``get(category)`` - Return appropriate table
  - Auto-strips sex suffix for lookup
  - Exception handling for missing PDFs

Analysis & Querying
^^^^^^^^^^^^^^^^^^^

**PerformanceCatalogue**
  - Ordered collection of Performance objects
  - **Filtering**: by athlete, event, date range, YOS, category, club
  - **Ranking**: Top N, ranking position
  - **Statistics**: mean, median, std dev
  - **Grouping**: group by athlete, event, YOS
  - **Method chaining**: ``cat.filter(...).top(10)``

Data Flow Examples
------------------

Simple Import & Query
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

    athle.fr HTML
         ↓
    AthleFrImporter.fetch_data()
         ↓
    AthleFrImporter.parse_performances()
         ↓
    LocalDataStore (Parquet)
         ↓
    importer.load_from_parquet()
         ↓
    PerformanceCatalogue
         ↓
    Query/Analysis

Medallion-Based Workflow
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

    Raw athle.fr
         ↓
    Bronze Layer (immutable)
         ↓
    Transform + Clean + Score
         ↓
    Silver Layer (processed)
         ↓
    Aggregate + Denormalize
         ↓
    Gold Layer (analytics)
         ↓
    PerformanceCatalogue / Dashboard

Design Principles
-----------------

**Normalization**
  - Athlete, Club, Event are separate entities
  - Performance references these entities
  - Prevents data redundancy

**Immutability**
  - Core domain objects are frozen dataclasses
  - Thread-safe, predictable behavior
  - Bronze layer immutable for auditing

**Extensibility**
  - PerformanceImporter is abstract
  - ScoringTable is abstract
  - DataStore is abstract
  - New implementations without modifying existing code

**Separation of Concerns**
  - Import layer handles data retrieval
  - Storage layer handles persistence
  - Medallion layer handles processing
  - Catalogue layer handles querying

**Configuration Over Convention**
  - Storage location configurable
  - Scoring tables swappable
  - Transformation pipelines customizable
  - No hardcoded paths or assumptions

Standards & Formats
-------------------

**Performance Data Format**
  - Parquet for efficient storage and querying
  - perf_id: unique identifier per performance
  - Dates: ISO 8601 format
  - Times: floating point seconds
  - Distances: floating point meters
  - Measurements: "time" or "distance"

**Year of Season (YOS)**
  - Athletics year: September 1 → August 31
  - 2026 YOS = Sept 2025 through Aug 2026
  - Auto-computed from performance date

**Column Naming**
  - snake_case for all columns
  - Consistent across importers
  - English names (no accented characters in code)

**Date Handling**
  - ISO 8601 format in storage
  - Timezone-naive (assumes local/event timezone)
  - Year-of-season computed from calendar date

Performance Considerations
--------------------------

**Medallion Layers**
  - Bronze: Minimal processing, stores everything
  - Silver: CPU-bound transformation (single-threaded default)
  - Gold: SQL/Pandas aggregations (can parallelize)

**Storage Backend**
  - Local: Fast (limited by disk speed, ~50k files/directory limit)
  - S3: Network latency (~100ms), unlimited scale, concurrent access

**Scoring Lookup**
  - WorldAthletics table: 70k+ rows, ~10ms lookup
  - French youth tables: 100-500 rows, <1ms lookup
  - Batch scoring preferred over row-by-row

**Parquet Files**
  - Columnar format, good compression
  - Supports partial reads (queries on subset of columns)
  - Auto-partitioning on write for large tables

Extensibility Points
--------------------

**Add New Importer**

Implement ``PerformanceImporter``:

.. code-block:: python

    class MyCSVImporter(PerformanceImporter):
        @property
        def source_name(self):
            return "my_csv"

        def fetch_data(self, file_path, **kwargs):
            # Read CSV file
            return pd.read_csv(file_path)

        def parse_performances(self, df):
            # Map columns, convert types
            return df.rename(columns={...})

**Add New Scoring Table**

Implement ``ScoringTable``:

.. code-block:: python

    class MyCustomScoringTable(ScoringTable):
        @property
        def applicable_categories(self):
            return ["SE", "M1", "M2"]  # Age categories

        def score(self, performance, **kwargs):
            # Custom scoring logic
            return points

        def available_events(self):
            return ["100m", "200m", ...]

**Add New Storage Backend**

Implement ``DataStore``:

.. code-block:: python

    class GoogleCloudStorageBackend(DataStore):
        def read_parquet(self, path):
            # Read from GCS
            pass

        def write_parquet(self, df, path):
            # Write to GCS
            pass

See Also
--------

- :doc:`guide_data_ingestion` - Data ingestion process
- :doc:`guide_storage` - Storage configuration
- :doc:`guide_medallion` - Medallion architecture details
- Source code: ``athletics_performance/`` package
