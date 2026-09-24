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
and read dynamically when building distributions. The version is
maintained by release-please (see [Creating a Release](#creating-a-release));
do not bump it manually in your PRs.

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

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        cas = client.cas.get_by_id(id="CAS1")
        cas.number
        # '7732-18-5'
        ```

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

        !!! example
            ```python
            cas = client.cas.get_by_id(id="CAS1")
            cas.number
            # '7732-18-5'
            ```

        Parameters
        ----------
        id : str
            The CAS ID.

        Returns
        -------
        Cas
            The fully populated CAS. See [`Cas`][albert.resources.cas.Cas].
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

#### Examples: use `!!! example` admonitions, placed before `Parameters`

Use `!!! example` admonitions -- they render as a styled purple box. Placement is critical:

**Always place `!!! example` in the description block, before the first numpy section.** Every numpy section (`Parameters`, `Attributes`, `Methods`, `Returns`, `Notes`, `Raises`) renders its content as a table. Any markdown placed after the last entry of a section -- including admonitions -- is absorbed into that section and rendered as a stray table row.

**Method docstrings** -- place before `Parameters`:

```python
def get_by_id(self, *, id: str) -> Cas:
    """Get a single CAS by its ID.

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        cas = client.cas.get_by_id(id="CAS1")
        cas.number
        # '7732-18-5'
        ```

    Parameters
    ----------
    id : str
        The CAS ID.

    Returns
    -------
    Cas
        The fully populated CAS. See [`Cas`][albert.resources.cas.Cas].
    """
```

**Class docstrings** (collections and resources alike) -- place before `Parameters` or `Attributes`, whichever comes first. Do not place after `Methods` or `Attributes` -- those render as tables too.

**Do not** wrap examples in `Examples\n--------` -- it adds a redundant "Examples:" label above the box.
**Do not** use a bare ` ```python ` fence inside an `Examples` numpy section -- it loses the box styling entirely.

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

Documentation is versioned with [mike](https://github.com/jimporter/mike) and deployed automatically by CircleCI:

1. **On every merge into `main`**, the `deploy_docs` job (mode `dev`) builds the docs and runs `mike deploy --update-aliases dev`, publishing the bleeding-edge docs under the `dev` alias.
2. **On every release tag**, the `deploy_docs` job (mode `release`) runs `mike deploy --update-aliases <version> latest`, publishing versioned docs and pointing `latest` at the new release.

Both push to the `gh-pages` branch, which GitHub Pages serves.

#### Manually Triggering a Docs Deployment

If needed, a maintainer can re-deploy the dev docs from a local checkout:

```bash
git checkout main
git pull origin main
uv sync
git fetch origin gh-pages:gh-pages
uv run mike deploy --push --update-aliases dev
```

Do not push the `gh-pages` branch directly; always deploy through `mike` so the versioned site structure is preserved.

## Creating a Release

Releases are automated with [release-please](https://github.com/googleapis/release-please). There is no manual version bumping and no manual "Draft a new release" step.

### How it works

1. **Merge PRs with Conventional Commit titles.** The PR Title GitHub Action enforces the format, and release-please uses it to classify changes: `feat:` is a minor bump, `fix:` is a patch bump, and `feat!:` / a breaking-change marker is a major bump. This is why the format in [Commit Guidelines](#commit-guidelines) matters.
2. **release-please maintains a release PR.** On every push to `main`, the `release-please` GitHub Action (`.github/workflows/release-please.yml`, running as the `release-catalyst` bot) opens or updates a PR titled `chore(main): release X.Y.Z`. The PR bumps `__version__` in `src/albert/__init__.py`, updates `.release-please-manifest.json`, and generates the new `CHANGELOG.md` section from the merged commit titles. The workflow can also be triggered manually from the Actions tab.
3. **A maintainer merges the release PR.** release-please then creates the `vX.Y.Z` git tag and publishes the GitHub Release with generated notes. Nothing else is edited by hand.
4. **The tag triggers the CircleCI `release` workflow** (`.circleci/config.yml`), which:
    * Validates the tag matches `__version__` in `src/albert/__init__.py` (`scripts/validate_release_tag.py`)
    * Builds and publishes the package to PyPI
    * Publishes the public AWS Lambda layers across the runtime/architecture/region matrix and appends their ARNs to the GitHub Release (see `docs/lambda.md`)
    * Deploys the versioned documentation with `mike deploy <version> latest` (see [Deploying Documentation](#deploying-documentation))

### Prereleases from the `next` branch

The `next` branch has its own release-please configuration (`release-please-config-next.json`) that cuts beta prereleases (e.g. `v1.35.0-beta0`) using the same flow: merge to `next`, merge the bot's `chore(next): release ...` PR, and the tag pipeline publishes the prerelease.

Note: Only designated Albert team members have permissions to merge release PRs.
