#!/usr/bin/env python3
"""Migrate NumPy ``Attributes`` class-docstring sections to Pydantic attribute docstrings.

Albert SDK models inherit ``use_attribute_docstrings=True`` from
``BaseAlbertModel``. Pydantic emits those docstrings as JSON Schema
``description`` values; class-level ``Attributes`` blocks do not.

This script:
1. Parses ``Attributes`` entries from each Pydantic model class docstring.
2. Inserts an attribute docstring immediately after each matching field definition.
3. Removes the ``Attributes`` section from the class docstring.

Skips fields that already have an attribute docstring or ``Field(description=...)``.
Only processes model classes (subclasses of ``BaseAlbertModel`` by name heuristic).

Usage:
    uv run python scripts/migrate_attributes_docstrings.py [--dry-run] [paths...]
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = [
    ROOT / "src/albert/resources",
    ROOT / "src/albert/core/shared/models",
]

NUMPY_SECTIONS = frozenset(
    {
        "Parameters",
        "Attributes",
        "Methods",
        "Returns",
        "Raises",
        "Notes",
        "See Also",
        "Yields",
        "Examples",
    }
)

BASE_MODEL_NAMES = frozenset(
    {
        "BaseAlbertModel",
        "BaseResource",
        "BaseSessionResource",
        "BaseTaggedResource",
        "AuditFields",
        "EntityLink",
        "EntityLinkWithName",
        "LocalizedNames",
        "PatchModel",
        "TaggedBaseModel",
    }
)


@dataclass
class ClassEdit:
    class_lineno: int
    docstring_lineno: int | None = None
    docstring_end_lineno: int | None = None
    new_class_docstring: str | None = None
    insertions: list[tuple[int, list[str]]] = field(default_factory=list)
    migrated: int = 0
    skipped: int = 0


def _base_names(node: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def collect_model_class_names(trees: list[ast.Module]) -> set[str]:
    """Fixpoint: every class inheriting (directly or indirectly) from a base model."""
    known = set(BASE_MODEL_NAMES)
    class_bases: dict[str, set[str]] = {}
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_bases[node.name] = _base_names(node)

    changed = True
    while changed:
        changed = False
        for name, bases in class_bases.items():
            if name in known:
                continue
            if bases & known:
                known.add(name)
                changed = True
    return known


def is_model_class(node: ast.ClassDef, known_models: set[str]) -> bool:
    if not node.bases:
        return False
    if node.name in known_models:
        return True
    return bool(_base_names(node) & known_models)


def parse_numpy_attributes(docstring: str) -> dict[str, str]:
    """Parse ``Attributes`` section into ``{field_name: description}``."""
    lines = docstring.splitlines()
    start: int | None = None
    for i, line in enumerate(lines):
        stripped = line.strip().rstrip(":")
        if stripped == "Attributes":
            start = i + 1
            if start < len(lines) and lines[start].strip().replace("-", "") == "":
                start += 1
            break
    if start is None:
        return {}

    attributes: dict[str, str] = {}
    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.split()[0].rstrip(":") in NUMPY_SECTIONS and " : " not in stripped:
            break

        sep = " : " if " : " in stripped else ": "
        if sep not in stripped:
            i += 1
            continue

        name, _type_part = stripped.split(sep, 1)
        name = name.strip()
        if not name.replace("_", "").isalnum():
            i += 1
            continue

        desc_parts: list[str] = []
        i += 1
        while i < len(lines):
            follow = lines[i]
            if not follow.strip():
                i += 1
                continue
            if not follow.startswith(" ") and not follow.startswith("\t"):
                break
            follow_stripped = follow.strip()
            if " : " in follow_stripped or ": " in follow_stripped:
                maybe_name = follow_stripped.split(" : ", 1)[0].split(": ", 1)[0].strip()
                if maybe_name.replace("_", "").replace(".", "").isalnum():
                    break
            desc_parts.append(follow_stripped)
            i += 1

        if desc_parts:
            attributes[name] = " ".join(desc_parts)

    return attributes


def strip_attributes_section(docstring: str) -> str:
    lines = docstring.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip().rstrip(":")
        if stripped == "Attributes":
            i += 1
            if i < len(lines) and lines[i].strip().replace("-", "") == "":
                i += 1
            while i < len(lines):
                if (
                    lines[i].strip()
                    and lines[i].strip().split()[0].rstrip(":") in NUMPY_SECTIONS
                    and " : " not in lines[i]
                ):
                    break
                i += 1
            while out and not out[-1].strip():
                out.pop()
            continue
        out.append(lines[i])
        i += 1
    text = "\n".join(out)
    while text.endswith("\n\n\n"):
        text = text[:-1]
    return text


def has_field_description(node: ast.AnnAssign) -> bool:
    if not isinstance(node.value, ast.Call):
        return False
    func = node.value.func
    if isinstance(func, ast.Name) and func.id == "Field":
        return any(kw.arg == "description" for kw in node.value.keywords)
    if isinstance(func, ast.Attribute) and func.attr == "Field":
        return any(kw.arg == "description" for kw in node.value.keywords)
    return False


def field_name_from_target(target: ast.expr) -> str | None:
    if isinstance(target, ast.Name):
        return target.id
    return None


def next_is_attribute_docstring(body: list[ast.stmt], idx: int) -> bool:
    if idx + 1 >= len(body):
        return False
    nxt = body[idx + 1]
    return (
        isinstance(nxt, ast.Expr)
        and isinstance(nxt.value, ast.Constant)
        and isinstance(nxt.value.value, str)
    )


def format_docstring_line(desc: str, indent: str) -> str:
    escaped = desc.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return f'{indent}"""{escaped}"""'


def process_class(
    node: ast.ClassDef, source_lines: list[str], known_models: set[str]
) -> ClassEdit | None:
    if not is_model_class(node, known_models):
        return None
    if not node.body:
        return None
    doc_node = node.body[0]
    if not isinstance(doc_node, ast.Expr) or not isinstance(doc_node.value, ast.Constant):
        return None
    if not isinstance(doc_node.value.value, str):
        return None

    docstring = doc_node.value.value
    attributes = parse_numpy_attributes(docstring)
    if not attributes:
        return None

    edit = ClassEdit(
        class_lineno=node.lineno,
        docstring_lineno=doc_node.lineno,
        docstring_end_lineno=doc_node.end_lineno,
    )
    body_stmts = node.body[1:] if isinstance(node.body[0], ast.Expr) else node.body

    for idx, stmt in enumerate(body_stmts):
        if not isinstance(stmt, ast.AnnAssign):
            continue
        fname = field_name_from_target(stmt.target)
        if not fname or fname not in attributes:
            continue
        if has_field_description(stmt):
            edit.skipped += 1
            continue
        if next_is_attribute_docstring(body_stmts, idx):
            edit.skipped += 1
            continue

        end_line = stmt.end_lineno or stmt.lineno
        indent = " " * 4
        for line in source_lines[stmt.lineno - 1 : end_line]:
            if line.strip():
                indent = line[: len(line) - len(line.lstrip())]
                break

        edit.insertions.append((end_line, [format_docstring_line(attributes[fname], indent)]))
        edit.migrated += 1

    if edit.migrated == 0 and edit.skipped == 0:
        return None

    new_doc = strip_attributes_section(docstring)
    if new_doc != docstring:
        edit.new_class_docstring = new_doc

    return edit if edit.migrated or edit.new_class_docstring else None


@dataclass
class DocstringReplacement:
    start_lineno: int
    end_lineno: int
    new_doc: str


def apply_class_docstring(
    source_lines: list[str],
    *,
    start_lineno: int,
    end_lineno: int,
    new_doc: str,
) -> None:
    """Replace a class docstring spanning ``start_lineno``..``end_lineno`` (1-based)."""
    start_idx = start_lineno - 1
    end_idx = end_lineno - 1
    if end_idx >= len(source_lines):
        raise IndexError(
            f"docstring end line {end_lineno} out of range (file has {len(source_lines)} lines)"
        )
    first = source_lines[start_idx]
    prefix = first[: first.index('"""')]
    suffix = ""
    last = source_lines[end_idx]
    if last.count('"""') >= 2 and start_idx == end_idx:
        after = last.split('"""', 2)
        if len(after) == 3:
            suffix = after[2]
    elif '"""' in last:
        suffix = last[last.rindex('"""') + 3 :]

    replacement = f'{prefix}"""{new_doc}"""{suffix}'
    source_lines[start_idx : end_idx + 1] = [replacement]


def apply_edits(
    plain_lines: list[str],
    *,
    docstring_replacements: list[DocstringReplacement],
    insertions: list[tuple[int, list[str]]],
) -> None:
    """Apply all edits bottom-up so AST line numbers stay valid."""
    ops: list[tuple[int, str, object]] = []
    for rep in docstring_replacements:
        ops.append((rep.end_lineno, "doc", rep))
    for line_no, lines_to_insert in insertions:
        ops.append((line_no, "insert", (line_no, lines_to_insert)))

    for _, kind, payload in sorted(ops, key=lambda item: item[0], reverse=True):
        if kind == "insert":
            insert_at, lines_to_insert = payload  # type: ignore[misc]
            assert isinstance(insert_at, int)
            assert isinstance(lines_to_insert, list)
            for offset, new_line in enumerate(lines_to_insert):
                plain_lines.insert(insert_at + offset, new_line)
        else:
            rep = payload
            assert isinstance(rep, DocstringReplacement)
            apply_class_docstring(
                plain_lines,
                start_lineno=rep.start_lineno,
                end_lineno=rep.end_lineno,
                new_doc=rep.new_doc,
            )


def process_file(path: Path, *, dry_run: bool, known_models: set[str]) -> tuple[int, int, int]:
    source = path.read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print(f"SKIP {path}: syntax error: {exc}", file=sys.stderr)
        return 0, 0, 0

    plain_lines = source.splitlines()
    class_edits: list[ClassEdit] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            edit = process_class(node, plain_lines, known_models)
            if edit:
                class_edits.append(edit)

    if not class_edits:
        return 0, 0, 0

    insertions: list[tuple[int, list[str]]] = []
    docstring_replacements: list[DocstringReplacement] = []
    total_migrated = 0
    total_skipped = 0
    for edit in class_edits:
        total_migrated += edit.migrated
        total_skipped += edit.skipped
        insertions.extend(edit.insertions)
        if (
            edit.new_class_docstring is not None
            and edit.docstring_lineno
            and edit.docstring_end_lineno
        ):
            docstring_replacements.append(
                DocstringReplacement(
                    start_lineno=edit.docstring_lineno,
                    end_lineno=edit.docstring_end_lineno,
                    new_doc=edit.new_class_docstring,
                )
            )

    if dry_run:
        print(
            f"DRY {path}: {len(class_edits)} classes, "
            f"{total_migrated} fields migrated, {total_skipped} skipped"
        )
        return len(class_edits), total_migrated, total_skipped

    apply_edits(
        plain_lines,
        docstring_replacements=docstring_replacements,
        insertions=insertions,
    )

    path.write_text("\n".join(plain_lines) + ("\n" if plain_lines else ""))
    print(
        f"OK  {path}: {len(class_edits)} classes, "
        f"{total_migrated} fields migrated, {total_skipped} skipped"
    )
    return len(class_edits), total_migrated, total_skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("paths", nargs="*", type=Path, default=DEFAULT_PATHS)
    args = parser.parse_args()

    files: list[Path] = []
    for p in args.paths:
        if p.is_file() and p.suffix == ".py":
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.py")))

    trees: list[ast.Module] = []
    for f in files:
        try:
            trees.append(ast.parse(f.read_text()))
        except SyntaxError as exc:
            print(f"SKIP {f}: syntax error: {exc}", file=sys.stderr)

    known_models = collect_model_class_names(trees)

    classes = migrated = skipped = 0
    for f in files:
        c, m, s = process_file(f, dry_run=args.dry_run, known_models=known_models)
        classes += c
        migrated += m
        skipped += s

    print(f"\nTotal: {classes} classes, {migrated} fields migrated, {skipped} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
