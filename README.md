# athletics-performance

[![PyPI version](https://badge.fury.io/py/athletics_performance.svg)](https://pypi.org/project/athletics_performance/)
[![Test and Lint](https://github.com/AthleticClubLyonnais/athletics-performance/workflows/Test%20and%20Lint/badge.svg)](https://github.com/AthleticClubLyonnais/athletics-performance/actions)
[![Documentation](https://github.com/AthleticClubLyonnais/athletics-performance/workflows/Build%20Documentation/badge.svg)](https://github.com/AthleticClubLyonnais/athletics-performance/actions)

Python package for managing athletics results data — athletes, clubs, events, and performances — following a normalised relational model.

Built for the **Athletic Club du Lyonnais (ACL)**.

## Package contents

| Module | Class / Object | Description |
|---|---|---|
| `athlete` | `Athlete` | Frozen dataclass: `licence`, `last_name`, `first_name`, `yob`, `sex`. Computes FFA age-group category via `category(yos)` and `category_code(yob, yos[, sex])`. |
| `club` | `Club` | Frozen dataclass: `club_id` (6 chars), `name`. Auto-derives `dept_code`, `ligue_code`, `ligue_name` from the club ID. |
| `club` | `DEPARTMENT_TO_LIGUE` | Mapping `dept_code → (ligue_code, ligue_name)` for all French departments + DOM-COM. |
| `club_membership` | `ClubMembership` | Tracks an athlete's membership period in a club (`athlete_id`, `club_id`, `start_date`, `end_date`). |
| `event` | `Event` | Frozen dataclass: `event_id`, `name`, `measurement` (`"time"`/`"distance"`), `unit` (`"s"`/`"m"`). |
| `performance` | `Performance` | Normalised performance record. Accepts `Athlete`/`Event` objects or raw IDs. Parses result strings, handles date formats, computes `yos` (year of season). |
| `scoring_tables` | `ScoringTables` | World Athletics scoring table calculator. |

## Installation

```bash
pip install athletics_performance
```

## Quick start

```python
from datetime import date
from athletics_performance import Athlete, Club, Event, ClubMembership, Performance

# Athlete
athlete = Athlete(licence="2275784", last_name="Perrin", first_name="Guillaume", yob=1982, sex="M")
print(athlete.full_name)          # "Guillaume Perrin"
print(athlete.category(2026))     # "M1M"

# Club (dept_code and ligue derived automatically from club_id)
club = Club(club_id="069106", name="ACL")
print(club.dept_code)    # "069"
print(club.ligue_code)   # "ARA"
print(club.ligue_name)   # "Auvergne-Rhône-Alpes"

# Club membership
membership = ClubMembership(athlete_id="2275784", club_id="069106", start_date=date(2022, 1, 1))
print(membership.is_active())   # True

# Event
event = Event(event_id="100m", name="100 mètres", measurement="time", unit="s")

# Performance (via Athlete + Event objects, or raw IDs)
perf = Performance(
    perf_id="P1",
    date=date(2026, 3, 15),
    result_value="12.34",
    measurement="time",
    unit="s",
    athlete=athlete,
    event=event,
    club_id_snapshot="069106",
    category_snapshot="M1M",
)
print(perf.result_value)   # 12.34
print(perf.yos)            # 2026
```

## Data model

```
athletes      licence (PK), last_name, first_name, yob, sex
clubs         club_id (PK, 6 chars), name  →  dept_code, ligue_code, ligue_name
events        event_id (PK), name, measurement, unit
memberships   athlete_id (FK), club_id (FK), start_date, end_date
performances  perf_id (PK), athlete_id (FK), event_id (FK), date, result_value,
              measurement, unit, venue, club_id_snapshot, category_snapshot, notes
```

## Development

To contribute to the project, please refer to [CONTRIBUTING.md](CONTRIBUTING.md).

### Quick start with development

```bash
# Clone and set up environment
git clone https://github.com/AthleticClubLyonnais/athletics-performance.git
cd athletics-performance

# Install with uv (Python 3.13+)
uv sync --all-groups
uv run pre-commit install

# Run tests
uv run pytest --cov

# Lint and format
uv run ruff check .
uv run ruff format .

# Build documentation locally
cd docs
uv run sphinx-autobuild . _build/html
```

## Release Process

1. Update version in commits/tags (tags determine publication)
2. Create a PR with your changes
3. Merge to `main`
4. Create a git tag: `git tag v1.0.0` (matches `v*` pattern)
5. Push tag: `git push origin v1.0.0`
6. GitHub Actions automatically:
   - Runs tests and linting
   - Builds and publishes to [PyPI](https://pypi.org/project/athletics_performance/)
   - Deploys documentation to GitHub Pages

## License

This project is licensed under the [ACL License](LICENSE.txt).