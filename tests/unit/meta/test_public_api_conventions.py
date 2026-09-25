"""Repo-wide static guards for public-API signature conventions.

Turns three `AGENTS.md` / `OPINIONS.md` rules into failing tests instead of relying on
review discipline:

- Every public method on a collection, resource, or client class is keyword-only
  after ``self``/``cls``.
- Every ``search``/``get_all`` method that has a ``max_items`` parameter defaults it
  to ``None``.
- No public collection method exposes ``offset`` or ``limit``.

Known offenders are pinned in per-rule ``KNOWN_*_VIOLATIONS`` frozensets. Do not add
entries to these sets for new code; only remove an entry once the underlying method is
fixed (the test fails loudly if a listed entry no longer violates the rule, so the
allowlist can only shrink).
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import NamedTuple

from pydantic import BaseModel

import albert.collections as collections_pkg
import albert.resources as resources_pkg
from albert.client import Albert, AsyncAlbert
from albert.collections.base import BaseCollection


class _MethodCase(NamedTuple):
    label: str
    member: object


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


def _iter_module_classes(pkg, base: type | None = None) -> list[type]:
    """Classes defined directly in each top-level module of ``pkg`` (no re-exports)."""
    pkg_dir = pkg.__file__.rsplit("/", 1)[0]
    classes: list[type] = []
    for mod_info in pkgutil.iter_modules([pkg_dir]):
        if mod_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{pkg.__name__}.{mod_info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module.__name__:
                continue
            if base is not None and not issubclass(obj, base):
                continue
            classes.append(obj)
    return classes


def _collection_classes() -> list[type]:
    return _iter_module_classes(collections_pkg, BaseCollection)


def _resource_model_classes() -> list[type[BaseModel]]:
    return _iter_module_classes(resources_pkg, BaseModel)


def _pydantic_machinery_names(cls: type) -> set[str]:
    """Method names pydantic itself invokes as validators/serializers/lifecycle hooks.

    These are not caller-facing public methods even though they lack a leading
    underscore, so they are excluded from the keyword-only check.
    """
    names = {"model_post_init"}
    decorators = getattr(cls, "__pydantic_decorators__", None)
    if decorators is not None:
        for group_name in (
            "field_serializers",
            "field_validators",
            "model_validators",
            "validators",
            "model_serializers",
        ):
            names.update(getattr(decorators, group_name).keys())
    return names


def _public_methods(
    cls: type, *, exclude: frozenset[str] = frozenset()
) -> list[tuple[str, object]]:
    """Public (non-dunder, non-underscore) methods/properties-excluded, defined on ``cls`` itself."""
    methods = []
    for name, member in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        if member.__qualname__.split(".")[0] != cls.__name__:
            continue
        if name in exclude:
            continue
        methods.append((name, member))
    return methods


def _positional_params(member) -> list[str]:
    """Parameter names (after self/cls) that are not keyword-only."""
    params = list(inspect.signature(member).parameters.values())
    if params and params[0].name in ("self", "cls"):
        params = params[1:]
    return [
        p.name
        for p in params
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]


def _all_public_params(member) -> list[str]:
    """All parameter names after self/cls, regardless of kind."""
    params = list(inspect.signature(member).parameters.values())
    if params and params[0].name in ("self", "cls"):
        params = params[1:]
    return [p.name for p in params]


def _keyword_only_cases() -> list[_MethodCase]:
    cases: list[_MethodCase] = []
    for cls in _collection_classes():
        for name, member in _public_methods(cls):
            cases.append(_MethodCase(f"{cls.__module__}.{cls.__name__}.{name}", member))
    for cls in _resource_model_classes():
        machinery = _pydantic_machinery_names(cls)
        for name, member in _public_methods(cls, exclude=frozenset(machinery)):
            cases.append(_MethodCase(f"{cls.__module__}.{cls.__name__}.{name}", member))
    for cls in (Albert, AsyncAlbert):
        for name, member in _public_methods(cls):
            cases.append(_MethodCase(f"{cls.__module__}.{cls.__name__}.{name}", member))
    return cases


KEYWORD_ONLY_CASES = _keyword_only_cases()

# Pre-existing; remove entries as they are fixed. Do not add new ones.
KNOWN_KEYWORD_ONLY_VIOLATIONS: frozenset[str] = frozenset(
    {
        "albert.collections.attachments.AttachmentCollection.upload_and_attach_file_as_note",
        "albert.collections.files.FileCollection.sign_and_upload_file",
        "albert.collections.inventory.InventoryCollection.get_facet_by_name",
        "albert.collections.workflows.WorkflowCollection.get_all",
        "albert.resources.sheets.Column.recolor_cells",
        "albert.resources.sheets.Column.rename",
        "albert.resources.sheets.Row.recolor_cells",
        "albert.resources.workflows.Workflow.get_interval_id",
    }
)


def test_public_methods_are_keyword_only() -> None:
    """Test that every public method takes only keyword-only parameters after self/cls."""
    offenders = {case.label for case in KEYWORD_ONLY_CASES if _positional_params(case.member)}
    _assert_matches_allowlist(
        offenders, KNOWN_KEYWORD_ONLY_VIOLATIONS, rule="keyword-only-argument"
    )


def _search_get_all_cases() -> list[_MethodCase]:
    cases: list[_MethodCase] = []
    for cls in _collection_classes():
        for name, member in _public_methods(cls):
            if name in ("search", "get_all"):
                cases.append(_MethodCase(f"{cls.__module__}.{cls.__name__}.{name}", member))
    return cases


SEARCH_GET_ALL_CASES = [
    case
    for case in _search_get_all_cases()
    if "max_items" in inspect.signature(case.member).parameters
]

# Pre-existing; remove entries as they are fixed. Do not add new ones.
KNOWN_MAX_ITEMS_VIOLATIONS: frozenset[str] = frozenset()


def test_search_and_get_all_max_items_defaults_to_none() -> None:
    """Test that search()/get_all() never truncate results via a non-None max_items default."""
    offenders = {
        case.label
        for case in SEARCH_GET_ALL_CASES
        if inspect.signature(case.member).parameters["max_items"].default is not None
    }
    _assert_matches_allowlist(offenders, KNOWN_MAX_ITEMS_VIOLATIONS, rule="max_items-default")


COLLECTION_METHOD_CASES = [
    _MethodCase(f"{cls.__module__}.{cls.__name__}.{name}", member)
    for cls in _collection_classes()
    for name, member in _public_methods(cls)
]

# Pre-existing; remove entries as they are fixed. Do not add new ones.
KNOWN_OFFSET_LIMIT_VIOLATIONS: frozenset[str] = frozenset(
    {
        "albert.collections.batch_data.BatchDataCollection.get_by_id",
        "albert.collections.btinsight.BTInsightCollection.search",
        "albert.collections.custom_templates.CustomTemplatesCollection.search",
        "albert.collections.data_templates.DataTemplateCollection.get_all",
        "albert.collections.data_templates.DataTemplateCollection.search",
        "albert.collections.inventory.InventoryCollection.get_all",
        "albert.collections.inventory.InventoryCollection.search",
        "albert.collections.lots.LotCollection.search",
        "albert.collections.parameter_groups.ParameterGroupCollection.get_all",
        "albert.collections.parameter_groups.ParameterGroupCollection.search",
        "albert.collections.projects.ProjectCollection.document_search",
        "albert.collections.projects.ProjectCollection.get_all",
        "albert.collections.projects.ProjectCollection.search",
        "albert.collections.tasks.TaskCollection.get_all",
        "albert.collections.tasks.TaskCollection.get_history",
        "albert.collections.tasks.TaskCollection.search",
        "albert.collections.users.UserCollection.search",
    }
)


def test_no_offset_or_limit_public_parameters() -> None:
    """Test that no public collection method exposes offset or limit as a parameter."""
    offenders = {
        case.label
        for case in COLLECTION_METHOD_CASES
        if set(_all_public_params(case.member)) & {"offset", "limit"}
    }
    _assert_matches_allowlist(
        offenders, KNOWN_OFFSET_LIMIT_VIOLATIONS, rule="offset/limit-parameter"
    )
