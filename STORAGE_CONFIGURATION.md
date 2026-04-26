# Storage Configuration Guide

Athletics Performance supports flexible data storage backends, allowing you to store your (potentially large) performance databases independently of the installed package.

## Storage Options

### 1. Local Filesystem (Default)

Store data on your local machine:

```python
from athletics_performance.importers import AthleFrImporter
from athletics_performance.storage import LocalDataStore

# Use default location (~/.athletics_performance/data/)
importer = AthleFrImporter()

# Or specify a custom local path
data_store = LocalDataStore('/data/athletics')
importer = AthleFrImporter(data_store=data_store)

# Import performances
importer.import_to_parquet(club_id="069106", season=2026)
```

### 2. AWS S3

Store data in AWS S3 for scalability and cloud integration:

```python
from athletics_performance.importers import AthleFrImporter
from athletics_performance.storage import S3DataStore

data_store = S3DataStore(
    bucket='my-athletics-bucket',
    prefix='performances',  # Subdirectory in bucket
    region_name='eu-west-1'
)
importer = AthleFrImporter(data_store=data_store)

# Import performances (stored in S3)
importer.import_to_parquet(club_id="069106", season=2026)
```

### 3. Configuration via Environment Variables

Define storage location via environment variables instead of code:

```bash
# Local filesystem
export ATHLETICS_STORAGE_TYPE=local
export ATHLETICS_STORAGE_PATH=/data/athletics

# Or S3
export ATHLETICS_STORAGE_TYPE=s3
export ATHLETICS_S3_BUCKET=my-athletics-bucket
export ATHLETICS_S3_PREFIX=performances
export ATHLETICS_AWS_REGION=eu-west-1
```

Then use the importer without specifying storage:

```python
from athletics_performance.importers import AthleFrImporter

importer = AthleFrImporter()  # Uses env vars automatically
```

### 4. Dynamic Configuration

Choose storage at runtime:

```python
from athletics_performance.storage import get_default_data_store
from athletics_performance.importers import AthleFrImporter

# Read from config file or environment
storage_config = {
    'type': 's3',
    'bucket': 'my-bucket',
    'prefix': 'performances'
}

data_store = get_default_data_store(storage_config)
importer = AthleFrImporter(data_store=data_store)
```

## Medallion Architecture

Organize your performance data across three layers:

### Bronze Layer (Raw)
Unprocessed data directly from importers:

```python
from athletics_performance.medallion import PerformanceMedallion

medallion = PerformanceMedallion(data_store)

# Save raw import
medallion.save_bronze(raw_df, 'ac_lyon_april_2026')

# Load later
raw_data = medallion.load_bronze('ac_lyon_april_2026')
```

### Silver Layer (Processed)
Cleaned, validated, deduplicated data with computed features:

```python
# Process and save to silver
medallion.save_silver(
    cleaned_df,
    'ac_lyon_april_2026_processed'
)

# Or use pipeline for systematic processing
processed = medallion.process_pipeline(
    bronze_name='ac_lyon_april_2026',
    silver_name='ac_lyon_april_2026_processed',
    transformations=[
        lambda df: df.drop_duplicates(subset=['perf_id']),
        lambda df: df.assign(wa_points=df['performance'].apply(compute_score)),
        lambda df: df[df['wa_points'].notna()],  # Filter valid scores
    ]
)
```

### Gold Layer (Analytics)
Aggregated, denormalized data ready for visualization:

```python
def compute_club_records(df):
    """Create club records dataset for dashboard."""
    return df.loc[df.groupby('event_name')['result_value'].idxmin()]

# Create gold layer
records = medallion.analytics_pipeline(
    silver_name='ac_lyon_april_2026_processed',
    gold_name='ac_lyon_records',
    aggregation_func=compute_club_records
)
```

## Benefits of This Architecture

| Aspect | Benefit |
|--------|---------|
| **Data Lineage** | Trace any analytics result back to raw source data |
| **Auditability** | Raw data preserved unchanged for compliance/verification |
| **Flexibility** | Refine processing without losing raw data |
| **Reproducibility** | Regenerate all layers from bronze if needed |
| **Performance** | Gold layer optimized for fast queries and visualizations |
| **Scalability** | Works seamlessly with both local and cloud storage |

## Complete Example Workflow

```python
import pandas as pd
from athletics_performance.importers import AthleFrImporter
from athletics_performance.storage import S3DataStore
from athletics_performance.medallion import PerformanceMedallion

# 1. Setup cloud storage
data_store = S3DataStore(
    bucket='my-athletics-data',
    prefix='2026-season'
)

# 2. Import (Bronze)
importer = AthleFrImporter(data_store=data_store)
importer.import_to_parquet(
    club_id='069106',
    season=2026,
    handle_duplicates='skip'  # Skip if already imported
)

# 3. Process (Silver)
medallion = PerformanceMedallion(data_store)

medallion.process_pipeline(
    bronze_name='athle_fr_performances.parquet',
    silver_name='ac_lyon_2026_processed',
    transformations=[
        lambda df: df.drop_duplicates(subset=['perf_id']),
        lambda df: df[df['performance'].str.len() > 0],  # Clean
        lambda df: df.assign(
            result_float=lambda x: pd.to_numeric(x['performance'], errors='coerce')
        ),
    ],
    overwrite=False
)

# 4. Analytics (Gold)
def club_records(df):
    """Minimum time for each event."""
    return df.loc[df.groupby('event_name')['result_float'].idxmin()]

medallion.analytics_pipeline(
    silver_name='ac_lyon_2026_processed',
    gold_name='ac_lyon_records',
    aggregation_func=club_records,
    overwrite=True
)

# 5. Analyze
records = medallion.load_gold('ac_lyon_records')
print(f"Club has {len(records)} records across events")
print(records[['athlete_name', 'event_name', 'result_float', 'date']])
```

## Storage Comparison

### Local Filesystem
- **Pros**: Simple, no external dependencies, fast
- **Cons**: Limited scalability, tied to single machine
- **Use case**: Development, single-site deployments, local analysis

### AWS S3
- **Pros**: Scalable, multi-user access, cloud integration
- **Cons**: Requires AWS account, costs, network dependencies
- **Use case**: Enterprise, shared resources, data analytics platforms

## Migration Between Backends

```python
# Read from S3
s3_store = S3DataStore('old-bucket', 'data')
old_importer = AthleFrImporter(data_store=s3_store)
df = old_importer.load_from_parquet('performances.parquet')

# Write to local
local_store = LocalDataStore('/data/athletics')
new_importer = AthleFrImporter(data_store=local_store)
new_importer.data_store.write_parquet(df, 'performances.parquet')
```

## Best Practices

1. **Separate data from code**: Never store performance data in package directories
2. **Version your transformations**: Document which version of processing generated each silver/gold layer
3. **Immutable bronze**: Treat bronze layer as read-only source of truth
4. **Document aggregations**: Clearly document how gold layer was computed from silver
5. **Use medallion for lineage**: Track data flow from raw to analytics using layers
6. **Test transformations**: Validate deduplication and scoring logic before production
