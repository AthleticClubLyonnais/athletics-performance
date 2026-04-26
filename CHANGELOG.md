# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Event Registry Expansion**: Extended event registry from 24 to 36 events covering all BE and MI French youth athletics categories (not in World Athletics referential)
- **Event Mapping Validation System**: New module for detecting unrecognized events and validating bronze→silver event mappings with detailed reporting
- **Silver Layer Transformations**: Declarative YAML-based data corrections with full reproducibility and audit trail
  - `Correction`, `TransformationRule`, `CorrectionRecord` dataclasses for type-safe rule definitions
  - `load_transformation_rules()` to parse YAML transformation specs
  - `identify_performances()` with two selector types: perf_ids (explicit list) and condition (complex matching)
  - `apply_transformations()` to apply rules with automatic audit manifest generation
  - `verify_reproducibility()` to ensure same input + rules = identical output
  - `save/load_corrections_manifest()` for audit trail storage
  - `report_transformations()` for human-readable summaries
- **Transformation Manifests**: Full audit trail tracking all corrections (rule_id, perf_id, field, old_value, new_value, applied_date, reviewer, source_file)
- **Performance Visualization Module**: Interactive Plotly-based charts with HTML export
  - `PerformanceVisualizer` class with 8 visualization methods
  - Athlete progression, performance distribution, multi-athlete time series
  - Event performance matrix (athlete × event heatmap)
  - Ranking charts, category analysis, statistics dashboard, season comparison
  - `export_to_html()` and `export_individual_html()` for HTML dashboard export
  - Interactive hover tooltips, zoom/pan, legend filtering on all charts
  - Responsive design for desktop/tablet/mobile
- Guide documentation for transformations workflow (guide_transformations.rst)
- GitHub Actions workflow for automated PyPI publishing on tagged releases
- GitHub Actions workflow for automated documentation deployment to GitHub Pages
- GitHub Actions workflow for testing and linting on all PRs and pushes
- PyPI and build status badges in README
- Release process documentation in README

### Changed
- Enhanced README with development setup instructions and release process guide
- Updated README with event registry, event mapping validation, and transformations quick start examples
- Updated data ingestion pipeline diagram to show validation and transformation stages
- Expanded API reference to include data quality and transformation classes/functions

## Previous Releases

- See [GitHub Releases](https://github.com/AthleticClubLyonnais/athletics-performance/releases) for historical release notes
