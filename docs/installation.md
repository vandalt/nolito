# Installation

<!-- ## PyPI -->
<!---->
<!-- TODO: Add link if/when there is a release -->
<!-- The simplest way to install `nolito` is to install it from PyPI. -->
<!---->
<!-- ```bash -->
<!-- python -m pip install nolito -->
<!-- ``` -->

## From source

To install from source, use:

```bash
pip install git+https://github.com/vandalt/nolito.git
```

## For development

To install for development, first clone the repository locally and enter it:

```bash
git clone https://github.com/vandalt/nolito.git
cd nolito
```

Then install `nolito` in editable mode with the `test` and `docs` groups.
This can be done with Pip:

```bash
python -m pip install -U -e . --group test --group docs
```

or with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

The next subsections discuss how to perform various development tasks.
If you installed with pip, simply remove `uv run` from the commands.

### Building the documentation

You should then be able to build the docs with:

```bash
uv run make -C docs html
```

### Running the unit tests

Nolito uses [pytest](https://pytest.org/) for testing.
Unit tests never call the API and only ensure that the information flow through Nolito is working as expected.

```bash
uv run pytest
```

### Running the integration tests

Integration tests call the live Nolio API and are skipped by default.
They require OAuth to be configured as described in [Getting started](getting-started.md#configuring-the-nolio-api).
These tests are read-only and intentionally do not run in GitHub Actions.

To include integration tests when running `pytest`, explicitly add the `--run-integration` flag:

```bash
uv run pytest --run-integration
```

To run _only_ the integration tests, either specify the path to `tests/integration/` or add the `-m integration` flag.

To read more on how to set up and use `nolito`, see the [Getting Started guide](getting-started.md)
