# athletics-performance

[![PyPI version](https://badge.fury.io/py/athletics_performance.svg)](https://pypi.org/project/athletics_performance/)
[![Test and Lint](https://github.com/AthleticClubLyonnais/athletics-performance/workflows/Test%20and%20Lint/badge.svg)](https://github.com/AthleticClubLyonnais/athletics-performance/actions)
[![Documentation](https://github.com/AthleticClubLyonnais/athletics-performance/workflows/Build%20Documentation/badge.svg)](https://github.com/AthleticClubLyonnais/athletics-performance/actions)

A Python library for managing athletics results data — athletes, clubs, events, performances, and scoring tables — following a normalised relational model.

Built for the **Athletic Club du Lyonnais (ACL)**.

## Features

- **Athlete & Club Models** — Immutable dataclasses with automatic category computation and department/league derivation
- **Event Catalog** — Pre-configured events with measurement types (time/distance)
- **Performance Records** — Normalised performance data with automatic year-of-season computation
- **Performance Catalogue** — Query, filter, rank, and analyze collections of performances
- **World Athletics Scoring Tables** — Official 2025 scoring table lookup system with PDF-to-parquet conversion
- **Membership Tracking** — Track athlete club membership with active/inactive status

## Installation

```bash
pip install athletics_performance
```

Requires Python 3.13+

## Quick Start

### Athlete Management

```python
from athletics_performance import Athlete

# Create an athlete
athlete = Athlete(
    licence="2275784",
    last_name="Perrin",
    first_name="Guillaume",
    yob=1982,
    sex="M"
)

print(athlete.full_name)           # "Guillaume Perrin"
print(athlete.category(yos=2026))  # "M1M" (age category)
```

### Club Management

```python
from athletics_performance import Club, DEPARTMENT_TO_LIGUE

# Create a club
club = Club(club_id="069106", name="ACL")

# Automatically derived attributes
print(club.dept_code)    # "069"
print(club.ligue_code)   # "ARA"
print(club.ligue_name)   # "Auvergne-Rhône-Alpes"

# Access department-to-league mapping
print(DEPARTMENT_TO_LIGUE["069"])  # ("ARA", "Auvergne-Rhône-Alpes")
```

### Club Membership

```python
from datetime import date
from athletics_performance import ClubMembership

# Track athlete club membership
membership = ClubMembership(
    athlete_id="2275784",
    club_id="069106",
    start_date=date(2022, 1, 1),
    end_date=None  # Still active
)

print(membership.is_active())  # True
```

### Events

```python
from athletics_performance import Event, EVENT_CATALOG

# Create a custom event
event = Event(
    event_id="100m",
    name="100 mètres",
    measurement="time",
    unit="s"
)

# Access pre-configured event catalog
sprint = EVENT_CATALOG["100m"]
jump = EVENT_CATALOG["LJ"]  # Long jump

print(jump.measurement)  # "distance"
print(jump.unit)         # "m"
```

### Performance Records

```python
from datetime import date
from athletics_performance import Athlete, Event, Performance

athlete = Athlete(licence="2275784", last_name="Perrin", first_name="Guillaume", yob=1982, sex="M")
event = Event(event_id="100m", name="100 mètres", measurement="time", unit="s")

# Create performance with object references
perf = Performance(
    perf_id="P1",
    date=date(2026, 3, 15),
    result_value=12.34,
    measurement="time",
    unit="s",
    athlete=athlete,
    event=event,
    club_id_snapshot="069106",
    category_snapshot="M1M",
)

print(perf.result_value)  # 12.34
print(perf.yos)           # 2026 (year of season)

# Or create with raw IDs
perf2 = Performance(
    perf_id="P2",
    date=date(2026, 4, 10),
    result_value=12.10,
    measurement="time",
    unit="s",
    athlete_id="2275784",
    event_id="100m",
)
```

### Performance Catalogue

```python
from datetime import date
from athletics_performance import Performance, PerformanceCatalogue

# Create a collection of performances
p1 = Performance(perf_id="P1", date=date(2026, 3, 15), result_value=12.34,
                 measurement="time", unit="s", athlete_id="A1", event_id="100m")
p2 = Performance(perf_id="P2", date=date(2026, 4, 10), result_value=11.90,
                 measurement="time", unit="s", athlete_id="A2", event_id="100m")

cat = PerformanceCatalogue([p1, p2])

# Collection operations
print(len(cat))                    # 2
print(cat.record())                # Best performance (11.90)
print(cat.by_athlete_id("A1"))    # Performances by A1

# Chaining operations
filtered = cat.by_event_id("100m").by_athlete_id("A1")

# Statistics
cat.mean_result()  # Average result
cat.median_result() # Median result
```

### World Athletics Scoring Tables

```python
from athletics_performance import ScoringTables

# Load the pre-built scoring tables
tables = ScoringTables.load()

# Look up points for a performance
points = tables.lookup(sex="M", event="100m", performance=12.34)
print(points)  # World Athletics points for 12.34s in men's 100m
```

## API Reference

### Core Classes

| Class | Purpose |
|-------|---------|
| **Athlete** | Immutable athlete record with licence, name, birth year, sex, and age-category computation |
| **Club** | Club information with automatic department and league derivation |
| **Event** | Event definition with measurement type (time/distance) and unit (s/m) |
| **Performance** | Single performance record with athlete, event, result, and date |
| **PerformanceCatalogue** | Ordered collection of Performance objects with filtering, ranking, and statistics |
| **ClubMembership** | Track athlete membership in a club with active/inactive status |
| **ScoringTables** | World Athletics 2025 scoring table lookups |

### Constants

| Name | Purpose |
|------|---------|
| **EVENT_CATALOG** | Pre-configured dictionary of standard athletics events |
| **DEPARTMENT_TO_LIGUE** | Mapping from French department codes to league codes and names |

## Data Model

```
athletes
  ├─ licence (PK)
  ├─ last_name
  ├─ first_name
  ├─ yob (year of birth)
  └─ sex ("F" or "M")

clubs
  ├─ club_id (PK, 6 chars)
  ├─ name
  ├─ dept_code (derived)
  ├─ ligue_code (derived)
  └─ ligue_name (derived)

events
  ├─ event_id (PK)
  ├─ name
  ├─ measurement ("time" or "distance")
  └─ unit ("s" or "m")

memberships
  ├─ athlete_id (FK → athletes)
  ├─ club_id (FK → clubs)
  ├─ start_date
  └─ end_date (nullable)

performances
  ├─ perf_id (PK)
  ├─ athlete_id (FK → athletes)
  ├─ event_id (FK → events)
  ├─ date
  ├─ result_value
  ├─ measurement ("time" or "distance")
  ├─ unit ("s" or "m")
  ├─ venue
  ├─ club_id_snapshot
  ├─ category_snapshot
  └─ notes
```

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/AthleticClubLyonnais/athletics-performance.git
cd athletics-performance

# Install development environment (Python 3.13+)
uv sync --all-groups
uv run pre-commit install
```

### Running Tests

```bash
# Run all tests with coverage
uv run pytest --cov=athletics_performance --cov-report=term

# Run a specific test file
uv run pytest tests/test_athlete.py

# Run tests matching a pattern
uv run pytest -k "category"
```

### Code Quality

```bash
# Lint code
uv run ruff check athletics_performance tests

# Format code
uv run ruff format athletics_performance tests

# Check formatting without changing
uv run ruff format --check athletics_performance tests
```

### Documentation

```bash
# Build documentation locally
cd docs
uv run sphinx-autobuild . _build/html

# Then visit http://localhost:8000
```

### Common Tasks

```bash
# Run all pre-commit checks
uv run pre-commit run --all-files

# Run tests, lint, and format
task test
task pre-commit

# Build the package
uv build
```

## Release Process

### Creating a Release

1. **Prepare changes** on your branch
2. **Create PR** and merge to `main`
3. **Create a git tag** matching `v*`:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

4. **GitHub Actions automatically**:
   - Runs all tests and linting checks
   - Builds the distribution
   - Publishes to [PyPI](https://pypi.org/project/athletics_performance/)
   - Deploys documentation to GitHub Pages

### Version Management

- Versions are determined by git tags (e.g., `v1.0.0`)
- The VERSION file is kept in sync and should not be manually edited
- Follow [Semantic Versioning](https://semver.org/) for tag names

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines and [CHANGELOG.md](CHANGELOG.md) for release history.

## Testing

The repository includes unit tests and light integration tests:

```bash
# Run with coverage report
uv run pytest --cov=athletics_performance --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Documentation

Full documentation is available at the project's documentation site (built from `docs/`).

Generated via Sphinx with numpydoc-style docstrings.

## License

This project is licensed under the [ACL License](LICENSE.txt).

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Setting up your development environment
- Running tests and pre-commit checks
- Creating feature branches and pull requests
- Release procedures and tagging conventions
