"""Repo-wide static guards for docstring content conventions (`AGENTS.md`).

Turns five rules into failing tests instead of relying on review discipline:

- No Sphinx cross-reference roles (``:class:``, ``:meth:``, ``:attr:``, ``:func:``) in any
  docstring; ``mkdocstrings`` renders them as literal text instead of resolving links.
- No em dash character anywhere in a docstring (org language policy).
- ``!!! example`` admonitions sit before the first Numpy section header, never inside one.
- Every collection class docstring has a ``Methods`` section that lists every public method.
- Every ``update`` method on a collection has a ``Notes`` section.

Known offenders are pinned in per-rule ``KNOWN_*_VIOLATIONS`` frozensets. Do not add entries
to these sets for new code; only remove an entry once the underlying docstring is fixed (the
test fails loudly if a listed entry no longer violates the rule, so the allowlist can only
shrink).
"""

from __future__ import annotations

import ast
import importlib
import inspect
import pkgutil
import re
from pathlib import Path
from typing import NamedTuple

import albert
import albert.collections as collections_pkg
from albert.collections.base import BaseCollection

_SRC_ROOT = Path(albert.__file__).resolve().parent

_SPHINX_ROLE_RE = re.compile(r":(class|meth|attr|func):`")
_EM_DASH = "—"
_NUMPY_SECTIONS = ("Parameters", "Attributes", "Methods", "Returns", "Notes", "Raises")


def _assert_matches_allowlist(offenders: set[str], known: frozenset[str], *, rule: str) -> None:
    """Assert ``offenders`` exactly matches ``known`` (a two-way allowlist diff).

    New, un-allowlisted offenders must be fixed, not added to the allowlist. An
    allowlisted entry that no longer offends must be removed from the allowlist, so it
    can only shrink over time.
    """
    new = sorted(offenders - known)
    fixed = sorted(known - offenders)
    parts = []
    if new:
        parts.append(f"New {rule} violations (fix the code, do not allowlist):\n" + "\n".join(new))
    if fixed:
        parts.append(
            f"Allowlisted {rule} entries no longer violate; remove from the allowlist:\n"
            + "\n".join(fixed)
        )
    assert not parts, "\n\n".join(parts)


class _DocEntry(NamedTuple):
    qualname: str
    text: str


class _DocVisitor(ast.NodeVisitor):
    """Collect every docstring-like string literal in a module, keyed by qualified name.

    Covers module/class/function docstrings (standard first-statement position) and
    attribute docstrings (a bare string literal trailing a class-level annotated
    assignment, per the ``AGENTS.md`` field-documentation convention).
    """

    def __init__(self, module_name: str) -> None:
        self.module_name = module_name
        self.stack: list[str] = []
        self.entries: list[_DocEntry] = []

    def _qualname(self, name: str | None = None) -> str:
        parts = [self.module_name, *self.stack]
        if name:
            parts.append(name)
        return ".".join(parts)

    def visit_Module(self, node: ast.Module) -> None:
        doc = ast.get_docstring(node, clean=False)
        if doc:
            self.entries.append(_DocEntry(self._qualname(), doc))
        self._collect_attribute_docstrings(node.body)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        doc = ast.get_docstring(node, clean=False)
        if doc:
            self.entries.append(_DocEntry(self._qualname(node.name), doc))
        self.stack.append(node.name)
        self._collect_attribute_docstrings(node.body)
        self.generic_visit(node)
        self.stack.pop()

    def _visit_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        doc = ast.get_docstring(node, clean=False)
        if doc:
            self.entries.append(_DocEntry(self._qualname(node.name), doc))
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_func(node)

    def _collect_attribute_docstrings(self, body: list[ast.stmt]) -> None:
        for idx, stmt in enumerate(body):
            if not (isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)):
                continue
            if idx + 1 >= len(body):
                continue
            nxt = body[idx + 1]
            if (
                isinstance(nxt, ast.Expr)
                and isinstance(nxt.value, ast.Constant)
                and isinstance(nxt.value.value, str)
            ):
                qualname = self._qualname(stmt.target.id) + " (attribute)"
                self.entries.append(_DocEntry(qualname, nxt.value.value))


def _iter_all_docstrings() -> list[_DocEntry]:
    entries: list[_DocEntry] = []
    seen_qualnames: dict[str, int] = {}
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(_SRC_ROOT.parent).with_suffix("")
        module_name = ".".join(rel.parts)
        tree = ast.parse(path.read_text())
        visitor = _DocVisitor(module_name)
        visitor.visit(tree)
        for qualname, text in visitor.entries:
            # A handful of resource models redeclare a field (and its docstring) twice in
            # the same class body; disambiguate so parametrize ids/allowlist keys stay
            # unique instead of silently colliding.
            count = seen_qualnames.get(qualname, 0)
            seen_qualnames[qualname] = count + 1
            label = qualname if count == 0 else f"{qualname} #{count + 1}"
            entries.append(_DocEntry(label, text))
    return entries


ALL_DOCSTRINGS = _iter_all_docstrings()

# Pre-existing; remove entries as they are fixed. Do not add new ones.
KNOWN_SPHINX_ROLE_VIOLATIONS: frozenset[str] = frozenset()


def test_no_sphinx_roles_in_docstrings() -> None:
    """Test that docstrings use autorefs links, not Sphinx roles mkdocstrings can't resolve."""
    offenders = {entry.qualname for entry in ALL_DOCSTRINGS if _SPHINX_ROLE_RE.search(entry.text)}
    _assert_matches_allowlist(offenders, KNOWN_SPHINX_ROLE_VIOLATIONS, rule="Sphinx-role")


# Pre-existing; remove entries as they are fixed. Do not add new ones.
KNOWN_EM_DASH_VIOLATIONS: frozenset[str] = frozenset()


def test_no_em_dash_in_docstrings() -> None:
    """Test that docstrings avoid em dashes per org language policy."""
    offenders = {entry.qualname for entry in ALL_DOCSTRINGS if _EM_DASH in entry.text}
    _assert_matches_allowlist(offenders, KNOWN_EM_DASH_VIOLATIONS, rule="em-dash")


def _first_numpy_section_index(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        stripped = line.strip().rstrip(":")
        if (
            stripped in _NUMPY_SECTIONS
            and i + 1 < len(lines)
            and lines[i + 1].strip()
            and set(lines[i + 1].strip()) <= {"-"}
        ):
            return i
    return None


EXAMPLE_ADMONITION_CASES = [
    entry
    for entry in ALL_DOCSTRINGS
    if not entry.qualname.endswith(" (attribute)") and "!!! example" in entry.text
]

# Pre-existing; remove entries as they are fixed. Do not add new ones.
KNOWN_EXAMPLE_PLACEMENT_VIOLATIONS: frozenset[str] = frozenset()


def _example_misplaced(entry: _DocEntry) -> bool:
    lines = entry.text.splitlines()
    example_idx = next(i for i, line in enumerate(lines) if "!!! example" in line)
    section_idx = _first_numpy_section_index(lines)
    return section_idx is not None and example_idx > section_idx


def test_example_admonition_before_first_numpy_section() -> None:
    """Test that `!!! example` admonitions sit in the free-form description, not a section."""
    offenders = {entry.qualname for entry in EXAMPLE_ADMONITION_CASES if _example_misplaced(entry)}
    _assert_matches_allowlist(
        offenders, KNOWN_EXAMPLE_PLACEMENT_VIOLATIONS, rule="example-admonition-placement"
    )


def _iter_collection_classes() -> list[type]:
    pkg_dir = collections_pkg.__file__.rsplit("/", 1)[0]
    classes: list[type] = []
    for mod_info in pkgutil.iter_modules([pkg_dir]):
        if mod_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"albert.collections.{mod_info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module.__name__:
                continue
            if not issubclass(obj, BaseCollection):
                continue
            classes.append(obj)
    return classes


def _public_method_names(cls: type) -> list[str]:
    names = []
    for name, member in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        if member.__qualname__.split(".")[0] != cls.__name__:
            continue
        names.append(name)
    return names


COLLECTION_CLASSES = _iter_collection_classes()
COLLECTIONS_WITH_PUBLIC_METHODS = [cls for cls in COLLECTION_CLASSES if _public_method_names(cls)]

# Pre-existing; remove entries as they are fixed. Do not add new ones.
KNOWN_METHODS_SECTION_VIOLATIONS: frozenset[str] = frozenset()


def _missing_from_methods_section(cls: type) -> list[str] | None:
    """Return method names missing from the docstring's Methods section, or None if absent."""
    doc = inspect.getdoc(cls) or ""
    has_methods_section = any(line.strip().rstrip(":") == "Methods" for line in doc.splitlines())
    if not has_methods_section:
        return None
    missing = [
        name
        for name in _public_method_names(cls)
        if not re.search(rf"(?m)^\s*{re.escape(name)}\(", doc)
    ]
    return missing


def test_collection_docstring_has_complete_methods_section() -> None:
    """Test that every collection class docstring lists all its public methods under Methods."""
    offenders = set()
    for cls in COLLECTIONS_WITH_PUBLIC_METHODS:
        missing = _missing_from_methods_section(cls)
        if missing is None or missing:
            offenders.add(f"{cls.__module__}.{cls.__name__}")
    _assert_matches_allowlist(
        offenders, KNOWN_METHODS_SECTION_VIOLATIONS, rule="Methods-section-completeness"
    )


def _collection_update_methods() -> list[tuple[str, object]]:
    cases = []
    for cls in COLLECTION_CLASSES:
        member = cls.__dict__.get("update")
        if member is None or not inspect.isfunction(member):
            continue
        cases.append((f"{cls.__module__}.{cls.__name__}.update", member))
    return cases


UPDATE_METHOD_CASES = _collection_update_methods()

# Pre-existing; remove entries as they are fixed. Do not add new ones.
KNOWN_UPDATE_NOTES_VIOLATIONS: frozenset[str] = frozenset()


def _has_notes_section(member: object) -> bool:
    doc = inspect.getdoc(member) or ""
    return any(line.strip().rstrip(":") == "Notes" for line in doc.splitlines())


def test_update_method_has_notes_section() -> None:
    """Test that every collection update() docstring has a Notes section of patchable fields."""
    offenders = {label for label, member in UPDATE_METHOD_CASES if not _has_notes_section(member)}
    _assert_matches_allowlist(
        offenders, KNOWN_UPDATE_NOTES_VIOLATIONS, rule="update-Notes-section"
    )
