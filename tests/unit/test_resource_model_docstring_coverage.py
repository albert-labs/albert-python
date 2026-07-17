"""Guard against regressions in Pydantic attribute-docstring coverage."""

from __future__ import annotations

import ast
import importlib
import inspect
import pkgutil
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

from albert.core.base import BaseAlbertModel

_RESOURCES_PKG = importlib.import_module("albert.resources")
_RESOURCES_DIR = Path(_RESOURCES_PKG.__file__).resolve().parent


def _resource_model_classes() -> list[type[BaseModel]]:
    models: list[type[BaseModel]] = []
    for mod_info in pkgutil.iter_modules([str(_RESOURCES_DIR)]):
        if mod_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"albert.resources.{mod_info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module.__name__:
                continue
            if issubclass(obj, Enum):
                continue
            if not issubclass(obj, BaseAlbertModel):
                continue
            models.append(obj)
    return models


def _class_docstring_has_attributes_section(cls: type) -> bool:
    doc = inspect.getdoc(cls) or ""
    return any(line.strip().rstrip(":") == "Attributes" for line in doc.splitlines())


def _fields_with_source_attribute_docstrings(cls: type) -> set[str]:
    """Return field names declared on ``cls`` that have a trailing attribute docstring."""
    try:
        source = inspect.getsource(cls)
    except (OSError, TypeError):
        return set()
    tree = ast.parse(source)
    class_node = tree.body[0]
    if not isinstance(class_node, ast.ClassDef):
        return set()

    documented: set[str] = set()
    body = class_node.body
    for idx, stmt in enumerate(body):
        if not isinstance(stmt, ast.AnnAssign):
            continue
        if not isinstance(stmt.target, ast.Name):
            continue
        if idx + 1 >= len(body):
            continue
        nxt = body[idx + 1]
        if isinstance(nxt, ast.Expr) and isinstance(nxt.value, ast.Constant):
            if isinstance(nxt.value.value, str) and nxt.value.value.strip():
                documented.add(stmt.target.id)
    return documented


def test_resource_models_have_no_class_level_attributes_sections() -> None:
    offenders = [cls.__name__ for cls in _resource_model_classes() if _class_docstring_has_attributes_section(cls)]
    assert not offenders, f"Move Attributes docs to attribute docstrings: {offenders}"


def test_attribute_docstrings_emit_field_descriptions() -> None:
    """Every attribute docstring on a declared field must reach ``model_fields`` / JSON schema."""
    offenders: list[str] = []
    for cls in _resource_model_classes():
        for fname in _fields_with_source_attribute_docstrings(cls):
            field_info = cls.model_fields.get(fname)
            if field_info is None or not field_info.description:
                offenders.append(f"{cls.__name__}.{fname}")
    assert not offenders, "Attribute docstrings not wired to Pydantic descriptions: " + ", ".join(offenders)


def test_hazard_statement_fields_are_documented() -> None:
    from albert.resources.hazards import HazardStatement

    props = HazardStatement.model_json_schema()["properties"]
    assert props["name"]["description"].startswith("The text of the hazard statement")
