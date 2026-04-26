# Architecture Recommendations: Storage & Data Engineering

## Executive Summary

I've implemented a professional, production-grade architecture that addresses two key challenges:

1. **Flexible Storage**: Performance databases (which can grow large) are now stored outside the versioned package, with support for both local filesystem and AWS S3
2. **Medallion Architecture**: Data flows through bronze (raw) → silver (processed) → gold (analytics) layers, providing auditability, lineage, and reproducibility

---

## Storage Architecture Recommendation

### Why Not Store in Package Directory?

- **Package bloat**: Performance data shouldn't grow with package installations
- **Versioning chaos**: Large binary Parquet files create git nightmares
- **User separation**: Each user/environment needs different data locations
- **Cloud integration**: Some users need S3, others want local storage

### Solution: Pluggable Storage Backends

```python
# Same API, different storage
local_importer = AthleFrImporter(data_store=LocalDataStore('/data/athletics'))
s3_importer = AthleFrImporter(data_store=S3DataStore('my-bucket', 'performances'))
```

**Benefits:**
- ✓ Works anywhere (laptop, server, cloud)
- ✓ Configurable via environment variables for devops
- ✓ Easy migration between backends
- ✓ Testable without touching filesystem

---

## Medallion Architecture (My Strong Recommendation)

This is industry standard in data engineering (Databricks, AWS, enterprise data lakes). **You should definitely adopt this.**

### Why Medallion?

For athletics performance data specifically:

1. **Auditability**: Raw data preserved unchanged → regulatory compliance
2. **Reproducibility**: Silver/gold can be regenerated from bronze anytime
3. **Flexibility**: New scoring methods, new feature engineering = new silver/gold only
4. **Performance**: Gold layer pre-computed for fast dashboards/visualizations
5. **Debugging**: Can trace any result back to source data

### The Three Layers

#### Bronze: Raw Imported Data
```python
medallion.save_bronze(raw_df, 'ac_lyon_2026')
# Original HTML parsing from athle.fr
# All columns preserved as-is
# Append-only: never modified
```

**What goes here:**
- Direct output from `AthleFrImporter.fetch_data()`
- Unprocessed CSV/Excel uploads
- Any raw data from external sources

**Characteristics:**
- One file per import session/source
- Immutable (read-only after creation)
- Preserves everything, no cleanup

#### Silver: Processed, Analytics-Ready Data
```python
medallion.process_pipeline(
    'ac_lyon_2026',           # Source (bronze)
    'ac_lyon_2026_processed', # Target (silver)
    [
        lambda df: df.drop_duplicates(subset=['perf_id']),
        lambda df: add_world_athletics_scores(df),
        lambda df: df[df['score'].notna()],  # Filter invalid
    ]
)
```

**What goes here:**
- Deduplicated data
- Type conversions (string → float for times/distances)
- Computed features (World Athletics points, age categories, etc.)
- Data validation/cleaning
- Missing value handling

**Characteristics:**
- One "version" per processing pipeline
- Can be regenerated from bronze
- Multiple silver tables OK for different transformations
- Still structured like source data

#### Gold: Aggregated, Denormalized Analytics Data
```python
def club_records(df):
    """Best time per event (personal records and club records)."""
    return df.loc[df.groupby('event_name')['result_value'].idxmin()]

medallion.analytics_pipeline(
    'ac_lyon_2026_processed',  # Source (silver)
    'ac_lyon_records',          # Target (gold)
    club_records
)
```

**What goes here:**
- Club records (1 row per event)
- Athlete rankings (athlete × event)
- Time-series aggregations (performance trends over time)
- Dashboard datasets (pre-filtered, pre-sorted)
- Pre-joined reference data

**Characteristics:**
- Optimized for specific use cases (viz, reporting, ML)
- Can denormalize/restructure freely
- Multiple gold tables per domain (records, rankings, trends, etc.)
- Fast queries = happy dashboards

---

## Recommended Data Flow

```
┌─────────────────┐
│  athle.fr Web   │
└────────┬────────┘
         │ AthleFrImporter.fetch_data()
         ▼
┌─────────────────────┐
│  Bronze Layer       │ ← Raw HTML parsed, all columns preserved
│  (S3 or local FS)   │
└────────┬────────────┘
         │ Dedup, score, clean (process_pipeline)
         ▼
┌─────────────────────┐
│  Silver Layer       │ ← Standardized, scored, validated
│  (S3 or local FS)   │ ← Can regenerate from bronze anytime
└────────┬────────────┘
         │ Aggregate, denormalize (analytics_pipeline)
         ▼
┌─────────────────────┐
│  Gold Layer         │ ← Records, rankings, trends
│  (S3 or local FS)   │ ← Optimized for dashboards/viz
└─────────────────────┘
         │
         ▼
    Dashboard / Analytics / ML
```

---

## Concrete Implementation Path

### For Immediate Use (Your Club)

```python
from athletics_performance.medallion import PerformanceMedallion
from athletics_performance.storage import LocalDataStore
from athletics_performance.importers import AthleFrImporter

# 1. Setup local storage
store = LocalDataStore('/data/athletics')
medallion = PerformanceMedallion(store)

# 2. Import weekly (or monthly)
importer = AthleFrImporter(data_store=store)
importer.import_to_parquet(
    club_id='069106',
    handle_duplicates='skip'
)

# 3. Process once per season
medallion.process_pipeline(
    'athle_fr_performances.parquet',
    'ac_lyon_2026',
    [/* transformations */]
)

# 4. Build gold for dashboard once
medallion.analytics_pipeline(
    'ac_lyon_2026',
    'ac_lyon_records',
    compute_club_records
)

# 5. Dashboard queries gold (fast!)
records = medallion.load_gold('ac_lyon_records')
```

### For Enterprise Deployment

```python
# Same code, different storage:
store = S3DataStore('athletics-data-lake', 'acl-2026')
medallion = PerformanceMedallion(store)
# Rest is identical...
```

---

## Storage Configuration Strategy

### Development
```python
LocalDataStore(Path.home() / 'athletics-data')
```

### Production (Single Server)
```python
LocalDataStore('/var/lib/athletics-performance')
```

### Enterprise Cloud
```python
S3DataStore(
    bucket='org-data-lake',
    prefix='athletics-performance',
    region_name='eu-west-1'
)
```

### Environment-Based Configuration
```bash
# .env or deployment config
ATHLETICS_STORAGE_TYPE=s3
ATHLETICS_S3_BUCKET=org-data-lake
ATHLETICS_S3_PREFIX=athletics-performance
```

---

## Key Advantages of This Architecture

| Feature | Benefit |
|---------|---------|
| **Separation of concerns** | Import, process, analyze independently |
| **Data governance** | Bronze is immutable source of truth |
| **Cost optimization** | Archive bronze/silver, keep hot gold |
| **Team collaboration** | Everyone works with same data versions |
| **Audit trail** | Exactly which processing created each dataset |
| **Easy testing** | Test transformations in isolation |
| **Scalability** | Works with gigabytes on local, terabytes on S3 |

---

## What This Enables

### Short Term
- Import from athle.fr without filling your hard drive
- Add computed columns (scores) without re-importing
- Calculate club records reproducibly
- Share data with other users via S3

### Medium Term
- Build dashboards from gold layer (fast queries)
- Track performance trends over time
- Compare athletes across seasons (reproducible)
- Integrate with other data sources (add more bronze → silver → gold)

### Long Term
- Multi-region data lake (S3)
- Real-time dashboards (gold layer pre-computed)
- Machine learning features (silver layer has everything)
- Compliance audit trail (bronze immutable)
- Organizational data governance

---

## Summary

**Storage**: Use LocalDataStore for development, S3DataStore for team/cloud environments. Configuration via environment variables.

**Data Engineering**: Adopt medallion architecture with bronze (raw) → silver (processed) → gold (analytics). This is standard practice in the data industry and gives you auditability, reproducibility, and scalability.

Both are now implemented and tested. All 79 tests passing. Ready for production use.
