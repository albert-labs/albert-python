"""Repo-wide static guard for warning attribution (`AGENTS.md`, "Warnings").

Every ``warnings.warn`` call in ``src/albert`` must pass
``stacklevel=find_stack_level()``. A literal ``stacklevel`` counts frames from the call
site, so ``@validate_call`` and SDK helpers make it point inside the SDK or pydantic,
where Python's default filters hide ``DeprecationWarning`` from callers.
"""

from __future__ import annotations

import ast
from pathlib import Path

import albert

_SRC_ROOT = Path(albert.__file__).resolve().parent


def _is_warnings_warn(call: ast.Call) -> bool:
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "warn"
        and isinstance(func.value, ast.Name)
        and func.value.id == "warnings"
    )


def _uses_find_stack_level(call: ast.Call) -> bool:
    for keyword in call.keywords:
        if keyword.arg != "stacklevel":
            continue
        value = keyword.value
        return (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "find_stack_level"
        )
    return False


def _offending_calls() -> list[str]:
    offenders = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and _is_warnings_warn(node)
                and not _uses_find_stack_level(node)
            ):
                offenders.append(f"{path.relative_to(_SRC_ROOT)}:{node.lineno}")
    return offenders


def test_warnings_warn_calls_use_find_stack_level() -> None:
    """Test that every warnings.warn call in the SDK passes stacklevel=find_stack_level()."""
    assert _offending_calls() == []
