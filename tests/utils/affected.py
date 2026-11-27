"""Select only the integration tests affected by a set of changed files.

A pytest plugin, inactive unless ``--changed-files PATH`` is passed. ``PATH`` names a text
file with one repo-relative path per line (for example ``gh pr diff N --name-only``).

How a test is attributed to source modules, statically and offline:

- Test modules reach collections through ``client.<attr>`` (``async_client.<attr>`` for
  async collections), never by importing them. ``<attr>`` maps to a collection module via
  the ``Albert`` and ``AsyncAlbert`` properties in ``src/albert/client.py``.
- Fixtures in ``tests/integration/conftest.py`` do the same, so the attrs used by every
  fixture in a test's fixture closure count as dependencies of that test.
- Each dependency module is expanded to its transitive ``albert.*`` import closure (all
  import statements, including ones nested in functions), stopping at the import hubs.

A test is selected when its own file changed, when its dependency set intersects the
changed files, or when it cannot be attributed to any source module. Some changes (core,
shared test infrastructure, workflow) select everything. Over-selection is acceptable;
under-selection is the bug to avoid.

Run it locally::

    git diff --name-only origin/main...HEAD > /tmp/changed.txt &&
    uv run python -m pytest tests/integration -p tests.utils.affected \
        --changed-files /tmp/changed.txt --collect-only -q

``python -m pytest`` (not bare ``pytest``) puts the repo root on ``sys.path``, which
``-p tests.utils.affected`` needs to import the plugin.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import pytest

CLIENT_RECEIVERS = frozenset({"client", "async_client"})

HUBS = frozenset(
    {
        # Re-exports every collection and resource, so reaching it says nothing.
        "src/albert/__init__.py",
        # Imports every collection; the attr map already captures what a test uses.
        "src/albert/client.py",
    }
)

# Any change to these selects the full suite.
FULL_RUN_TRIGGERS = (
    # Package hub and client wiring: affect every collection.
    "src/albert/__init__.py",
    "src/albert/client.py",
    # Exception types are raised and asserted on everywhere.
    "src/albert/exceptions.py",
    # Session, auth, pagination and shared models underpin every call.
    "src/albert/core/",
    # Base class of every collection.
    "src/albert/collections/base.py",
    # Fixtures and seeding feed every integration test.
    "tests/integration/conftest.py",
    "tests/integration/seeding.py",
    "tests/integration/utils/",
    # Shared test helpers, including this plugin.
    "tests/utils/",
    # Would apply to every test if it ever exists.
    "tests/conftest.py",
    # Dependency and tool configuration changes behavior everywhere.
    "pyproject.toml",
    # The CI definition itself must be exercised in full.
    ".github/workflows/test.yml",
)

_CONFTEST = "tests/integration/conftest.py"
_CLIENT = "src/albert/client.py"
_STASH_KEY = pytest.StashKey[str]()


@dataclass(frozen=True)
class ItemInfo:
    """The facts about one collected test that selection needs."""

    node_id: str
    module: str
    """Repo-relative POSIX path of the test file."""

    fixtures: tuple[str, ...]
    """Names in the test's transitive fixture closure."""


def _rel(path: Path, src_root: Path) -> str:
    return path.relative_to(src_root.parent).as_posix()


def collection_attr_map(client_py: Path) -> dict[str, str]:
    """Map each client property name to the repo-relative module of its collection class.

    Built from the ``Albert`` and ``AsyncAlbert`` properties and the collection imports at
    the top of ``client_py`` (``src/albert/client.py``).
    """
    src_root = client_py.parent.parent
    tree = ast.parse(client_py.read_text())
    class_modules: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "albert.collections."
        ):
            module_path = _resolve_module(node.module, src_root)
            if module_path is not None:
                for alias in node.names:
                    class_modules[alias.asname or alias.name] = _rel(module_path, src_root)
    attr_map: dict[str, str] = {}
    for cls in tree.body:
        if isinstance(cls, ast.ClassDef) and cls.name in {"Albert", "AsyncAlbert"}:
            for fn in cls.body:
                if (
                    isinstance(fn, ast.FunctionDef)
                    and any(_dotted(d) == "property" for d in fn.decorator_list)
                    and isinstance(fn.returns, ast.Name)
                    and fn.returns.id in class_modules
                ):
                    attr_map[fn.name] = class_modules[fn.returns.id]
    return attr_map


def client_attrs(source: str) -> set[str]:
    """Return attribute names accessed on ``client`` or ``async_client`` in ``source``."""
    return _attrs_in(ast.parse(source))


def _attrs_in(tree: ast.AST) -> set[str]:
    return {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in CLIENT_RECEIVERS
    }


def fixture_client_attrs(conftest_source: str) -> dict[str, set[str]]:
    """Map each fixture name to the client attributes its body accesses."""
    result: dict[str, set[str]] = {}
    for node in ast.walk(ast.parse(conftest_source)):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        name = _fixture_name(node)
        if name is not None:
            result[name] = _attrs_in(node)
    return result


def _fixture_name(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    for deco in fn.decorator_list:
        call = deco if isinstance(deco, ast.Call) else None
        if _dotted(call.func if call else deco).split(".")[-1] == "fixture":
            if call is not None:
                for kw in call.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                        return str(kw.value.value)
            return fn.name
    return None


def _dotted(node: ast.expr) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _resolve_module(name: str, src_root: Path) -> Path | None:
    base = src_root.joinpath(*name.split("."))
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


@cache
def _direct_imports(path: str, mtime_ns: int, size: int, src_root: str) -> frozenset[str]:
    """Repo-relative paths of the ``albert.*`` modules ``path`` imports, nested imports included."""
    root = Path(src_root)
    names: list[str] = []
    for node in ast.walk(ast.parse(Path(path).read_text())):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.append(node.module)
            names.extend(f"{node.module}.{alias.name}" for alias in node.names)
    found: set[str] = set()
    for name in names:
        if name == "albert" or name.startswith("albert."):
            resolved = _resolve_module(name, root)
            if resolved is not None:
                found.add(_rel(resolved, root))
    return frozenset(found)


def import_closure(module: Path, *, src_root: Path, hubs: frozenset[str]) -> set[str]:
    """Return the transitive ``albert.*`` import closure of ``module``.

    ``src_root`` is the ``src`` directory; returned paths are relative to its parent (the
    repo root) in POSIX form. ``module`` itself is included. Hub modules are neither
    returned nor traversed.
    """
    repo_root = src_root.parent
    start = _rel(module, src_root)
    seen: set[str] = set()
    pending = [start]
    while pending:
        current = pending.pop()
        if current in seen or current in hubs:
            continue
        seen.add(current)
        path = repo_root / current
        stat = path.stat()
        pending.extend(_direct_imports(str(path), stat.st_mtime_ns, stat.st_size, str(src_root)))
    return seen


def is_full_run(changed: Iterable[str]) -> str | None:
    """Return the first changed path that forces a full run, or None."""
    for path in sorted(changed):
        for trigger in FULL_RUN_TRIGGERS:
            if path == trigger or (trigger.endswith("/") and path.startswith(trigger)):
                return path
    return None


def select(
    items: Sequence[ItemInfo],
    changed: set[str],
    *,
    repo_root: Path,
    attr_map: dict[str, str],
    fixture_attrs: dict[str, set[str]],
) -> tuple[list[str], list[str], str]:
    """Split ``items`` into selected and deselected node ids, with a reason line."""
    trigger = is_full_run(changed)
    if trigger is not None:
        return [i.node_id for i in items], [], f"full run (trigger: {trigger})"

    src_root = repo_root / "src"
    closures: dict[str, set[str]] = {}

    def closure_of(module_path: str) -> set[str]:
        if module_path not in closures:
            path = repo_root / module_path
            closures[module_path] = (
                import_closure(path, src_root=src_root, hubs=HUBS) if path.is_file() else set()
            )
        return closures[module_path]

    module_info: dict[str, tuple[set[str], set[str]]] = {}

    def module_deps(module: str) -> tuple[set[str], set[str]]:
        if module not in module_info:
            tree = ast.parse((repo_root / module).read_text())
            module_info[module] = (closure_of(module), _attrs_in(tree))
        return module_info[module]

    selected: list[str] = []
    deselected: list[str] = []
    for item in items:
        own_closure, own_attrs = module_deps(item.module)
        attrs = set(own_attrs)
        for name in item.fixtures:
            attrs |= fixture_attrs.get(name, set())
        deps = set(own_closure)
        for attr in attrs:
            if attr in attr_map:
                deps |= closure_of(attr_map[attr])
        deps -= {item.module}
        if item.module in changed or not deps or deps & changed:
            selected.append(item.node_id)
        else:
            deselected.append(item.node_id)

    shown = ", ".join(sorted(changed)[:5]) + (", ..." if len(changed) > 5 else "")
    reason = f"{len(selected)} selected, {len(deselected)} deselected (changed: {shown})"
    return selected, deselected, reason


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--changed-files",
        default=None,
        metavar="PATH",
        help="Select only tests affected by the repo-relative paths listed in PATH.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    option = config.getoption("--changed-files")
    if not option:
        return
    changed = {line.strip() for line in Path(option).read_text().splitlines() if line.strip()}
    root = Path(config.rootpath)
    infos = [
        ItemInfo(
            node_id=item.nodeid,
            module=item.path.relative_to(root).as_posix(),
            fixtures=tuple(item._fixtureinfo.names_closure),  # type: ignore[attr-defined]
        )
        for item in items
    ]
    selected, deselected, reason = select(
        infos,
        changed,
        repo_root=root,
        attr_map=collection_attr_map(root / _CLIENT),
        fixture_attrs=fixture_client_attrs((root / _CONFTEST).read_text()),
    )
    config.stash[_STASH_KEY] = f"affected-tests: {reason}"
    drop = set(deselected)
    removed = [item for item in items if item.nodeid in drop]
    if removed:
        config.hook.pytest_deselected(items=removed)
        items[:] = [item for item in items if item.nodeid not in drop]


def pytest_report_header(config: pytest.Config) -> str | None:
    return config.stash.get(_STASH_KEY, None)


def pytest_collection_finish(session: pytest.Session) -> None:
    config = session.config
    if config.option.collectonly and _STASH_KEY in config.stash:
        print(config.stash[_STASH_KEY])
