## Installation for Local Development

The package is built using the [uv](https://docs.astral.sh/uv/getting-started/installation/) build tool.
To get started, install uv on your system by running

```
# For Mac OS users
brew install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After that, the package and its dependencies can be installed
in your local virtual environment by running

```
uv sync
```

Follow the documentation on the [uv website](https://docs.astral.sh/uv/concepts/projects/) 
for additional project features such as managing dependencies, managing environments, 
and configuring Python project metadata.

### Dynamic Versioning

The package version is defined in the `src/albert/__init__.py` file
and read dynamically when building distributions.

### Publishing

TODO

## Code Style

This project uses [ruff](https://docs.astral.sh/ruff/) for both formatting and linting.
Formatting and linting rules are enforced in the CI process.

To check (or fix) your code formatting, you can run the commands

```
# Check
uv run ruff format . --check

# Fix
uv run ruff format .
```

To check (or fix) your code linting, you can run the commands

```
# Check
uv run ruff check .

# Fix
uv run ruff check . --fix
```

For VSCode users, there is also base workspace settings defined in `.vscode/settings.json` that enable
automatic fomatting and import sorting on-save using the
[Ruff for VSCode](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) extension.