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

## Dynamic Versioning

The package version is defined in the `src/albert/__init__.py` file
and read dynamically when building distributions.

## Releasing

Releasing the package is triggered manually through the creation of a GitHub Release.
When a GitHub Release is created with a version tag matching the form `v{version}`,
a CircleCI workflow is triggered that publishes the package to PyPI and builds the documentation.
Generally, releases are only created against the `main` branch on a cadence determined by the development team.

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

## Documentation

### Using Numpy-Style Docstrings

All **public methods and classes** in this repository should follow the **Numpy-style docstring format**. This ensures consistency and compatibility with `mkdocstrings` for automated documentation generation.

#### Example

```python
class Cas:
    """
    Represents a CAS entity.

    Attributes
    ----------
    number : str
        The CAS number.
    name : str, optional
        The name of the CAS.
    """

    def from_string(cls, *, number: str) -> "Cas":
        """
        Creates a Cas object from a string.

        Parameters
        ----------
        number : str
            The CAS number.

        Returns
        -------
        Cas
            The Cas object created from the string.
        """
        return cls(number=number)
```


When contributing new classes or methods, ensure *all public members* have properly formatted Numpy-style docstrings.

### Adding New Classes

To add coverage for a new microservice, you can add a page by doing the following:
 1. in the `docs/` folder make a new markdown file following the pattern of the others.
    For example:
    ```
    # cas.md

    ::: albert.collections.cas
    ```

2. In `mkdocs.yml` add a link to the `nav` section (Alphabetically Sorted) following the existing pattern.

### Testing Documentation Locally

Before pushing documentation changes, verify that everything is rendering correctly.

#### 1. Install dependencies (if not already installed):

```
uv sync
```

#### 2. Build and serve the documentation locally:

```
uv run mkdocs serve
```

#### 3. Open http://127.0.0.1:8000/ (or specified address) in your browser and navigate through the docs to confirm that:

- All references and links are resolving correctly.
- Docstrings are properly formatted.
- No missing or broken sections exist.

### Deploying Documentation
The documentation is automatically built and deployed to GitHub Pages when a pull request is merged into main.

#### How It Works

1. A PR is merged into main.
2. CircleCI runs the deploy_docs job, which:

    - Builds the latest version of the documentation using mkdocs build --clean.
    - Pushes the built docs to the gh-pages branch.
    - GitHub Pages automatically serves the latest docs

#### Manually Triggering a Docs Deployment
If needed, you can manually re-deploy the docs by running:

```
git checkout main
git pull origin main
uv run mkdocs build --clean
git push origin gh-pages
```