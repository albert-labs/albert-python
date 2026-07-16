# Contributing to Albert Python SDK

Thanks for your interest in contributing to the Albert Python SDK! We aim to make it as easy as possible to get started and see your changes released quickly.

---

## 🚀 Quickstart

1. **Clone** the repository:

    ```bash
    git clone https://github.com/your-username/albert-python.git
    cd albert-python
    ```

2. **Run** the setup script (installs all dependencies and hooks):

    ```bash
    ./setup.sh
    ```

3. **Create** a new branch for your work:

    ```bash
    git checkout -b my-awesome-feature
    ```

4. **Make your changes**, then commit. Pre-commit hooks and linting will run automatically.
5. **Push** your branch and open a Pull Request against `main`.

Your contribution could ship in days or weeks -- welcome aboard! 🚀

## Dynamic Versioning

The package version is defined in the `src/albert/__init__.py` file
and read dynamically when building distributions.

## Code Style

This project uses [ruff](https://docs.astral.sh/ruff/) for both formatting and linting.
Formatting and linting rules are enforced in the CI process.

To check (or fix) your code formatting, you can run the commands,

```bash
# Check
uv run ruff format . --check

# Fix
uv run ruff format .
```

To check (or fix) your code linting, you can run the commands

```bash
# Check
uv run ruff check .

# Fix
uv run ruff check . --fix
```

For VSCode users, there is also base workspace settings defined in `.vscode/settings.json` that enable
automatic fomatting and import sorting on-save using the
[Ruff for VSCode](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) extension.

## Commit Guidelines

We use the [Conventional Commits](https://www.conventionalcommits.org/) format:

```text
type(scope)!: summary
```

* `type`: one of `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `style`, `build`, `ci`, `perf`, `revert`
* `scope`: optional, a module or feature name (e.g., `auth`, `session`)
* `!`: optional, indicates a **breaking change**
* `summary`: short and clear — think “when applied, the SDK will…”

### Examples

```text
feat(auth): support token refresh
fix!: remove deprecated param handling
docs: clarify local dev setup
```

This keeps commit history readable and enables changelog automation.

## Documentation

### Using Numpy-Style Docstrings

All **public methods and classes** in this repository should follow the **Numpy-style docstring format**. Docs are generated from these docstrings with `mkdocstrings`, so a few formatting rules matter for the site to render correctly. Getting them right up front avoids tedious repo-wide clean-up later.

#### Example

```python
class CasCollection(BaseCollection):
    """Manage CAS entries in the Albert platform.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Methods
    -------
    get_by_id(id) -> Cas
        Get a single CAS by its ID.
    create(cas) -> Cas
        Create a new CAS.
    """

    def get_by_id(self, *, id: str) -> Cas:
        """Get a single CAS by its ID.

        Parameters
        ----------
        id : str
            The CAS ID.

        Returns
        -------
        Cas
            The fully populated CAS. See [`Cas`][albert.resources.cas.Cas].

        Examples
        --------
        ```python
        from albert import Albert

        client = Albert()
        cas = client.cas.get_by_id(id="CAS1")
        cas.number
        # '7732-18-5'
        ```
        """
        ...
```

Ensure *all public members* have properly formatted Numpy-style docstrings.

#### Cross-references: use autorefs, not Sphinx roles

`mkdocstrings` does **not** understand Sphinx roles — `:class:`, `:meth:`, `:attr:` render as literal text on the docs site. Link with autorefs syntax instead:

```text
[`DisplayName`][fully.qualified.path]
```

- The display text is the short name in backticks; the target is the fully-qualified dotted path.
- Fully qualify every target, even a sibling method in the same class, e.g.
  `` [`get_all`][albert.collections.cas.CasCollection.get_all] ``.
- The `autorefs` plugin (bundled with `mkdocstrings`) is enabled in `mkdocs.yml`. A target only resolves if that class/method is rendered on a docs page — if you reference something in an undocumented module, add a page for it (see [Adding New Classes](#adding-new-classes)) or don't link it.

#### Examples: use an `Examples` section with a bare code fence

Put runnable snippets under a Numpy `Examples` section using a plain ` ```python ` fence (as in the example above). **Do not** use `!!! example` admonitions: without a section header the admonition is absorbed into the preceding `Returns`/`Notes` section (it renders as a stray table row), and with one you get a duplicate "Examples / Example" heading.

- Instantiate the client zero-arg: `client = Albert()`. Show it once in the class-level example and reuse `client` afterward.
- Async collections use `async with AsyncAlbert() as client:` and `await`.
- Show returned values as `# comment` lines.

#### Wording conventions

Keep wording consistent across the SDK:

- Imperative mood: **Get** (reads), **Create**, **Update**, **Delete**, **Search** — not `Retrieve`/`Fetch`/`Register`/`Gets`.
- Class opener: `Manage <Entity> in the Albert platform.` (read-only collections use `Access <Entity> …`).
- `__init__`: `Initialize a/an <CollectionClass>.`
- Refer to identifiers as "by its ID"; use "fully populated" (not "fully hydrated").
- Describe **what** from the caller's perspective — never internal details (diffing, patching, HTTP, "returned by the API").
- No em dashes (`—`); use commas, colons, or parentheses.
- Beta features use the `(🧪 Beta)` badge (with a space).

### Adding New Classes

To add coverage for a new microservice, you can add a page by doing the following:

 1. in the `docs/` folder make a new markdown file following the pattern of the others.
    For example:

    ```markdown
    # cas.md

    ::: albert.collections.cas
    ```

 2. In `mkdocs.yml` add a link to the `nav` section (Alphabetically Sorted) following the existing pattern.

> **Note:** a class is only a valid autorefs cross-reference target once it is rendered on a docs page, so add pages for modules you link to. A package directory must contain an `__init__.py` for `mkdocstrings` to collect it (implicit namespace packages are not collectable).

### Testing Documentation Locally

Before pushing documentation changes, verify that everything is rendering correctly.

#### 1. Install dependencies (if not already installed)

```bash
uv sync
```

#### 2. Build and serve the documentation locally

```bash
uv run mkdocs serve
```

#### 3. Open <http://127.0.0.1:8000/> (or specified address) in your browser and navigate through the docs to confirm that

* All references and links are resolving correctly.
* Docstrings are properly formatted.
* No missing or broken sections exist.

### Deploying Documentation

The documentation is automatically built and deployed to GitHub Pages when a pull request is merged into main.

#### How It Works

1. A PR is merged into main.
2. CircleCI runs the deploy_docs job, which:

    * Builds the latest version of the documentation using mkdocs build --clean.
    * Pushes the built docs to the gh-pages branch.
    * GitHub Pages automatically serves the latest docs

#### Manually Triggering a Docs Deployment

If needed, you can manually re-deploy the docs by running:

```bash
git checkout main
git pull origin main
uv run mkdocs build --clean
git push origin gh-pages
```

## Creating a Release

1. Ensure the version in `src/albert/__init__.py` is updated to the desired release version
2. Go to the **Releases** section of the repository
3. Click **"Draft a new release"**
4. Create a new tag matching the version in `__init__.py` (e.g., if `__init__.py` has `__version__ = "0.3.0"`, use tag `v0.3.0`)
5. Click **"Generate release notes"** and review/edit as needed
6. Publish the release

The release will automatically trigger the CircleCI workflow to:

* Build and publish the package to PyPI
* Build and deploy the documentation

Note: Only designated Albert team members have permissions to create releases.
