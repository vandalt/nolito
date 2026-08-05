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

You should then be able to build the docs with:

```bash
uv run make -C docs html
```

and run the tests with:

```bash
uv run pytest
```

If you installed with pip, simply remove `uv run` from the commands above.

To read more on how to set up and use `nolito`, see the [Getting Started guide](getting-started.md)
