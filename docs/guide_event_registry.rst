Event Registry: Normalizing Event Names
=========================================

This guide explains how to use the event registry to normalize event names from various sources (athle.fr, CSVs, APIs) to canonical event IDs.

Why Event Normalization?
------------------------

Athletic event data from different sources uses inconsistent naming:

- athle.fr (French federation) uses French names: "Longueur", "Hauteur", "Poids"
- World Athletics uses codes: "LJ", "HJ", "SP"
- English systems use full names: "Long Jump", "High Jump", "Shot Put"

The event registry provides a single source of truth, mapping all synonyms to canonical event IDs (e.g., ``long_jump``), enabling:

- **Consistency**: Same event regardless of source
- **Deduplication**: Merging data from multiple sources
- **Analytics**: Aggregating performances across sources
- **Extensibility**: Adding new synonyms without code changes

Quick Start
-----------

.. code-block:: python

    from athletics_performance.events import EventRegistry

    registry = EventRegistry()  # Loads packaged event_registry.yaml

    # Resolve any synonym to canonical ID
    registry.resolve("longueur")  # French → "long_jump"
    registry.resolve("LJ")        # World Athletics code → "long_jump"
    registry.resolve("long jump") # English → "long_jump"
    registry.resolve("100m")      # Sprint → "100m"

    # Get event metadata
    metadata = registry.get_metadata("long_jump")
    print(f"Measurement: {metadata.measurement}")  # "distance"
    print(f"Unit: {metadata.unit}")                # "m"

Available Events
----------------

The registry includes 40+ athletic events:

**Track Events**
  - Sprints: 100m, 200m, 400m
  - Middle distance: 800m, 1500m
  - Long distance: 5000m, 10000m, marathon
  - Hurdles: 100m_hurdles, 110m_hurdles, 400m_hurdles
  - Steeplechase: steeplechase_3000m
  - Relays: relay_4x100m, relay_4x400m

**Field Events (Jumps)**
  - high_jump, long_jump, triple_jump, pole_vault

**Field Events (Throws)**
  - shot_put, discus, hammer, javelin

**Combined**
  - decathlon, heptathlon

Using the Registry in Silver Layer
-----------------------------------

The event registry is designed to be applied in the silver layer, during data processing:

.. code-block:: python

    import pandas as pd
    from athletics_performance.events import EventRegistry
    from athletics_performance.medallion import PerformanceMedallion

    registry = EventRegistry()

    # Silver layer transformation
    def normalize_events(df):
        """Normalize event names to canonical IDs."""
        df = df.copy()

        # Resolve each event name
        df['event_id'] = df['event_name'].apply(
            lambda name: registry.resolve(name)
        )

        # Remove rows with unrecognized events (optional)
        # Uncomment to skip unrecognized events:
        # df = df[df['event_id'].notna()]

        return df

    # Apply transformation
    medallion = PerformanceMedallion(store)
    silver_df = medallion.process_pipeline(
        bronze_name='ac_lyon_2026',
        silver_name='ac_lyon_2026_normalized',
        transformations=[normalize_events]
    )

Complete Example: Bronze → Silver → Gold
-----------------------------------------

.. code-block:: python

    import pandas as pd
    from athletics_performance.events import EventRegistry
    from athletics_performance.medallion import PerformanceMedallion
    from athletics_performance.storage import LocalDataStore

    # Setup
    store = LocalDataStore('/data/athletics')
    medallion = PerformanceMedallion(store)
    registry = EventRegistry()

    # Phase 1: Import (Bronze)
    # Assume raw data from athle.fr is already in bronze layer
    bronze = medallion.load_bronze('ac_lyon_2026')

    # Phase 2: Process (Silver) - Normalize events
    def process_with_normalized_events(df):
        """Transform bronze to silver with event normalization."""
        df = df.copy()

        # Deduplicate
        df = df.drop_duplicates(subset=['perf_id'])

        # Convert performance to numeric
        df['perf_float'] = pd.to_numeric(
            df['performance'],
            errors='coerce'
        )

        # Normalize event names to canonical IDs
        df['event_id'] = df['event_name'].apply(
            lambda name: registry.resolve(name)
        )

        # Filter out unrecognized events (optional)
        unrecognized = df[df['event_id'].isna()]
        if len(unrecognized) > 0:
            print(f"Warning: {len(unrecognized)} rows with unknown events")
            print(unrecognized['event_name'].unique())

        df = df[df['event_id'].notna()]

        # Filter valid performances
        df = df[df['perf_float'].notna()]
        df = df[df['perf_float'] > 0]

        return df

    silver_df = medallion.process_pipeline(
        bronze_name='ac_lyon_2026',
        silver_name='ac_lyon_2026_processed',
        transformations=[process_with_normalized_events]
    )

    # Phase 3: Analytics (Gold) - Aggregations by canonical event ID
    def club_records_by_event(df):
        """Best time per canonical event ID."""
        return df.loc[df.groupby('event_id')['perf_float'].idxmin()]

    records_df = medallion.analytics_pipeline(
        silver_name='ac_lyon_2026_processed',
        gold_name='ac_lyon_records',
        aggregation_func=club_records_by_event
    )

    # Phase 4: Analysis
    gold = medallion.load_gold('ac_lyon_records')

    # Find long jump record
    lj_record = gold[gold['event_id'] == 'long_jump']
    if len(lj_record) > 0:
        best = lj_record.iloc[0]
        print(f"Long Jump Record: {best['athlete_name']} - {best['perf_float']}m")

Handling Unrecognized Events
-----------------------------

When importing data from external sources, some event names may not be in the registry:

.. code-block:: python

    from athletics_performance.events import EventRegistry

    registry = EventRegistry()

    # Option 1: Resolve with None fallback
    event_id = registry.resolve("unknown_event")
    if event_id is None:
        # Handle unrecognized event
        print("Event not recognized")

    # Option 2: Use resolve_strict (raises error)
    try:
        event_id = registry.resolve_strict("unknown_event")
    except ValueError as e:
        print(f"Error: {e}")

    # Option 3: Check membership
    if "my_event" in registry:
        event_id = registry.resolve("my_event")
    else:
        print("Event not in registry")

Adding Custom Events
--------------------

Extend the registry with custom events by:

1. **Copy the packaged YAML:**

   .. code-block:: bash

       cp athletics_performance/data/event_registry.yaml ./custom_events.yaml

2. **Add your events:**

   .. code-block:: yaml

       events:
         my_custom_event:
           world_athletics_id: "MCE"
           measurement: time
           unit: s
           description: "My custom event"
           french_synonyms:
             - "mon événement"
           english_synonyms:
             - "my custom event"

3. **Load the custom registry:**

   .. code-block:: python

       from athletics_performance.events import EventRegistry

       registry = EventRegistry('./custom_events.yaml')
       registry.resolve("mon événement")  # Works!

Adding New Synonyms
--------------------

To add synonyms for existing events without modifying code:

1. **Edit event_registry.yaml:**

   Find the event and add to ``french_synonyms`` or ``english_synonyms``:

   .. code-block:: yaml

       long_jump:
         # ... existing fields ...
         french_synonyms:
           - "saut en longueur"
           - "longueur"
           - "saut longueur"
           - "new_synonym_here"  # Add here

2. **Reload the registry:**

   .. code-block:: python

       # New process picks up the changes
       registry = EventRegistry()
       registry.resolve("new_synonym_here")  # Works!

Event Metadata
--------------

Each event includes metadata for processing:

.. code-block:: python

    from athletics_performance.events import EventRegistry

    registry = EventRegistry()
    metadata = registry.get_metadata("100m")

    # Available fields:
    print(metadata.canonical_id)         # "100m"
    print(metadata.world_athletics_id)   # "100"
    print(metadata.measurement)          # "time"
    print(metadata.unit)                 # "s"
    print(metadata.description)          # "100 meters sprint"

Use metadata to:
  - Filter by measurement type (time vs distance)
  - Apply appropriate validation (times must be positive, distances must be realistic)
  - Format output (convert seconds to mm:ss, etc.)
  - Scoring (different scoring tables for time vs distance events)

Integration with Scoring
------------------------

Combine event normalization with scoring:

.. code-block:: python

    import pandas as pd
    from athletics_performance.events import EventRegistry
    from athletics_performance.scoring_tables import ScoringTableResolver

    registry = EventRegistry()
    scoring_resolver = ScoringTableResolver()

    def add_world_athletics_scores(df):
        """Normalize events and add World Athletics scores."""
        df = df.copy()

        # Normalize event ID
        df['event_id'] = df['event_name'].apply(
            lambda name: registry.resolve(name)
        )

        # Get World Athletics event code for scoring
        df['wa_event_code'] = df['event_id'].apply(
            lambda eid: registry.get_metadata(eid).world_athletics_id
            if eid and registry.get_metadata(eid) else None
        )

        # Add scores (requires athlete category)
        df['wa_points'] = df.apply(
            lambda row: score_performance(
                row['perf_float'],
                row['event_id'],
                row['category']  # Requires athlete category
            ),
            axis=1
        )

        return df

    def score_performance(perf_value, event_id, category):
        """Score a single performance."""
        try:
            metadata = registry.get_metadata(event_id)
            if not metadata:
                return 0

            # Get scoring table for category
            scoring_table = scoring_resolver.get(category)

            # Score based on measurement type
            if metadata.measurement == "time":
                # Times are in seconds, convert if needed
                return scoring_table.score(perf_value, event_id)
            elif metadata.measurement == "distance":
                # Distances are in meters
                return scoring_table.score(perf_value, event_id)
            else:
                return 0
        except:
            return 0

Testing Event Normalization
----------------------------

When testing silver layer transformations:

.. code-block:: python

    import pytest
    from athletics_performance.events import EventRegistry

    def test_event_normalization():
        """Test that event names are normalized correctly."""
        registry = EventRegistry()

        # Test data with various event name formats
        test_cases = [
            ("100m", "100m"),
            ("100 mètres", "100m"),
            ("longueur", "long_jump"),
            ("LJ", "long_jump"),
            ("poids", "shot_put"),
        ]

        for input_name, expected_id in test_cases:
            result = registry.resolve(input_name)
            assert result == expected_id, f"Failed for {input_name}"

    def test_silver_transformation_with_events():
        """Test silver layer transformation with event normalization."""
        registry = EventRegistry()
        medallion = PerformanceMedallion(store)

        # Create test data
        test_df = pd.DataFrame({
            'perf_id': ['p1', 'p2', 'p3'],
            'event_name': ['longueur', 'hauteur', 'poids'],
            'performance': [7.5, 1.95, 18.2],
        })

        # Save to bronze
        medallion.save_bronze(test_df, 'test_events')

        # Process through silver
        silver_df = medallion.process_pipeline(
            'test_events',
            'test_events_normalized',
            [normalize_events]
        )

        # Verify normalization
        assert list(silver_df['event_id']) == ['long_jump', 'high_jump', 'shot_put']

Key Benefits
------------

✓ **Consistency** - Same event ID regardless of source
✓ **Maintainability** - Add synonyms without code changes
✓ **Extensibility** - Support custom events via YAML
✓ **Data Quality** - Identify unrecognized events during processing
✓ **Integration** - Works seamlessly in medallion architecture
✓ **Multilingual** - French and English synonyms built-in
✓ **Standards** - Uses World Athletics official codes

See Also
--------

- :doc:`guide_medallion` - Silver layer processing
- :doc:`guide_data_ingestion` - Importing performance data
- `World Athletics Event Codes <https://worldathletics.org/>`_
- `French Athletics Federation <https://athle.fr/>`_
