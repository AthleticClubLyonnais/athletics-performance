# CLAUDE.md

This file provides working context for any Claude session opened on this repository.

## Project purpose

- Python library for modelling athletics results: athletes, clubs, events, performances, and scoring tables.
- Main domain: ACL athletics data, using a normalized relational model with a simple object-oriented API.
- Production code lives in `athletics_performance/`.

## Stack and tooling

- Required Python version: 3.13+
- Packaging: `flit`
- Environment and dependency management: `uv`
- Tests: `pytest`, `pytest-cov`
- Linting: `ruff`
- Documentation: `sphinx`, `numpydoc`, `sphinx-autobuild`
- Notebooks: `jupyter`

## Repository structure

- `athletics_performance/`: main package
- `athletics_performance/data/`: packaged data assets
- `tests/`: unit tests and light integration tests
- `docs/`: Sphinx documentation
- `notebooks/`: exploration and demonstration notebooks

## Coding conventions

- Prefer explicit domain models over scattered business logic.
- Keep the public API simple, readable, and object-oriented for `Athlete`, `Club`, `Event`, `Performance`, and `ScoringTables`.
- Follow the existing style: use frozen dataclasses when the entity is conceptually immutable.
- Keep attribute names aligned with the current domain vocabulary: `athlete_id`, `club_id`, `event_id`, `result_value`, `measurement`, `unit`, `yob`, `yos`.
- Avoid hidden side effects. Prefer deterministic, testable transformations.
- Add short, useful docstrings in the style already used in the project.
- Do not introduce new dependencies without a clear need.
- Preserve public package API compatibility where possible.

## Tests and validation

- Add or adjust tests in `tests/` for any observable behavior change.
- Prioritize unit tests around business logic, performance parsing, and scoring.
- Run tests with:

```bash
task test
```

- Direct execution with `uv`:

```bash
uv run pytest --cov=. --cov-report term
```

- Note: some `ScoringTables` tests depend on generated parquet data being present.

## Useful commands

```bash
task sync-dev
task test
task pre-commit
task doc
task serve-doc
uv run pre-commit install
```

## Documentation expectations

- Any significant API or business behavior change should be reflected in `README.md`, `docs/`, or both depending on scope.
- Documentation is built with Sphinx.

## Practical contribution rules

- Use `uv` to manage the local environment.
- Do not manually edit `athletics_performance/VERSION`.
- Avoid unrelated changes in the same patch.
- If a change affects business logic, validate at least the relevant tests.

## IEC 62304 notes

Current status:

- No explicit IEC 62304 requirements are formalized in this repository at the moment.
- Do not invent regulatory constraints that have not been confirmed by the team.

If this project enters a regulated software scope, document here explicitly:

- the applicable software safety class
- traceability requirements between code, tests, and requirements
- review and approval rules
- additional documentation requirements
- anomaly and change management constraints

Until then, treat this project as a business-focused Python library with an emphasis on clarity, reproducibility, and appropriate test coverage.

## Expectations for Claude

- Before editing code, read the files closest to the impacted area.
- Make minimal changes that fit the existing style.
- Validate behavior with the narrowest relevant test before broadening scope.
- If business intent is unclear, prefer a short explicit question or a stated hypothesis over an implicit assumption.