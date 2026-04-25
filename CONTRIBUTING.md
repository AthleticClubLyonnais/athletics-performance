# How to contribute

This project uses `uv` as a virtual environment and dependency manager.

## TL;DR:

- Open an issue
- Create a new branch for this issue
- Create a new Pull Request for this branch
- Make sure you're using a modern python version e.g. (check the version required in the **pyproject.toml**)
  ```bash
  # as a reminder (example)
  module purge
  module load python/3.13.3
  ```
- Install the dependencies (dev)
  ```bash
  task sync-dev
  ```
  - Install pre-commit hooks. This runs code before commiting to make sure your code meets the project coding standards. It does linting, formatting, cleaning of the jupyter notebook output cells.
  ```bash
  task pre-commit-install
  ```
- Edit the code
- Check that the documentation is generated correctly
  ```bash
  task serve-doc
  ```
- Commit your work on your branch and push your code
- Create a new tag on your branch formed like "X.Y.Z-rcN" where X.Y.Z is the version and N the number of the release candidate
*Example: 1.2.3-rc1*
- Test out your release candidate in real conditions
- If everything works as expected, validate the PR and create a release tag
*Example: 1.2.3*

### What you don't need to do

- **You don't need to modify the athletics_performance/VERSION file**
*Treat it as generated project metadata and keep it aligned with the release tag rather than editing it manually.*


### Continous integration (CI)

This repository is intended to work with a lightweight Python CI setup:

* linting: code is linted using ruff
* tests: an example function is tested. You'll need to edit the tested functions to make it suit your testing needs.
* package publication for tagged releases
* documentation generation for tagged releases


#### Taskfile

A Taskfile is provided to help you with basic python development operations
```sh
# Run unit tests
task test

# Create documentation
task doc
```

### What you need to do

#### Virtual environment

You can use `uv` when working on athletics_performance

```sh
uv sync
```

This creates a virtual environment in `.venv` and install all dependencies needed for development.
Use ``uv run <command>`` to run commands in the virtual environment.

See [uv documentation](https://docs.astral.sh/uv/guides/projects/#managing-dependencies) for more details.

## Tools

This repository template uses the following tools:

- [uv](https://docs.astral.sh/uv/) to manage the virtual environment and dependencies
- [ruff](https://docs.astral.sh/ruff/linter/) to lint the code
- [pytest](https://docs.pytest.org/en/7.4.x/) to run unit tests
- [flit](https://flit.readthedocs.io/en/latest/) to build and publish the package
- [sphinx](https://www.sphinx-doc.org/en/master/) to generate the documentation
- [pre-commit](https://pre-commit.com/) to verify your code is good enough to be commited
- [Taskfile](https://taskfile.dev/) to lighten syntax
