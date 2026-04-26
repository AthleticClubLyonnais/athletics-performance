Welcome to athletics-performance's documentation!
=================================================

Athletics Performance is a Python library for managing athletics results data with scoring, performance analysis, and data ingestion from external sources.

**Table of Contents**

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   guide_data_ingestion
   guide_storage
   guide_medallion
   guide_event_registry
   guide_transformations

.. toctree::
   :maxdepth: 2
   :caption: Architecture & Design

   architecture
   modules

Quick Links
-----------

- **Data Ingestion**: Import performances from athle.fr and other sources — :doc:`guide_data_ingestion`
- **Storage Configuration**: Store data locally or in AWS S3 — :doc:`guide_storage`
- **Medallion Architecture**: Bronze/Silver/Gold data layers — :doc:`guide_medallion`
- **Event Registry**: Normalize event names from multiple sources — :doc:`guide_event_registry`
- **Silver Layer Transformations**: Correct performances with reproducibility and audit trail — :doc:`guide_transformations`
- **System Architecture**: High-level system design — :doc:`architecture`
- **API Reference**: Complete class and function reference — :ref:`modindex`

Key Features
------------

**Core Models**
  - Athlete, Club, Event, Performance — normalized data model
  - PerformanceCatalogue — filter, query, and analyze performances
  - ClubMembership — track athlete affiliations over time

**Scoring & Analytics**
  - World Athletics 2025 scoring tables
  - French youth categories (BE, MI)
  - Custom scoring table support

**Data Ingestion**
  - Import from athle.fr (French athletics federation)
  - Extensible importer framework
  - Smart duplicate handling

**Storage & Processing**
  - Flexible storage (local filesystem or AWS S3)
  - Medallion architecture (bronze/silver/gold layers)
  - Reproducible data transformation pipelines

**Data Quality & Validation**
  - Event mapping validation with detailed reporting
  - Declarative YAML-based transformations
  - Full audit trail (who/what/when/why)
  - Reproducibility guarantee (same input + rules = identical output)

**Performance Analysis**
  - Filtering and ranking
  - Statistics and grouping
  - Method chaining for complex queries
