"""Pure helpers for building saved grid view filters and columns.

A view's saved filter map (see
[`ViewQuery`][albert.resources.views.ViewQuery]) is applied by the grid through the
entity's search, so the valid filter keys for a grid are exactly the filter
parameters of the matching collection's ``search`` method. These helpers derive
those keys from the collections themselves rather than duplicating a per-grid
mapping that would drift from the API.
"""

from __future__ import annotations

import inspect
import re
import typing
from functools import cache
from typing import Any

from albert.collections.attributes import AttributeCollection
from albert.collections.base import BaseCollection
from albert.collections.custom_templates import CustomTemplatesCollection
from albert.collections.data_columns import DataColumnCollection
from albert.collections.data_templates import DataTemplateCollection
from albert.collections.inventory import InventoryCollection
from albert.collections.parameter_groups import ParameterGroupCollection
from albert.collections.projects import ProjectCollection
from albert.collections.reports import ReportCollection
from albert.collections.tasks import TaskCollection
from albert.collections.teams import TeamCollection
from albert.collections.users import UserCollection
from albert.exceptions import AlbertException
from albert.resources.facet import FacetItem, FacetValue
from albert.resources.views import ViewColumn, ViewEntity, ViewFilter, ViewQuery

_ENTITY_COLLECTIONS: dict[ViewEntity, type[BaseCollection]] = {
    ViewEntity.PROJECTS: ProjectCollection,
    ViewEntity.TASKS: TaskCollection,
    ViewEntity.INVENTORIES: InventoryCollection,
    ViewEntity.DATA_TEMPLATES: DataTemplateCollection,
    ViewEntity.PARAMETER_GROUPS: ParameterGroupCollection,
    ViewEntity.DATA_COLUMNS: DataColumnCollection,
    ViewEntity.TEMPLATES: CustomTemplatesCollection,
    ViewEntity.REPORTS: ReportCollection,
    ViewEntity.TEAMS: TeamCollection,
    ViewEntity.USERS: UserCollection,
    ViewEntity.REFERENCE_ATTRIBUTES: AttributeCollection,
}

# Search route segments that differ from the entity value (mirror the owning
# collection's `base_path`).
_ENTITY_SEARCH_SEGMENTS: dict[ViewEntity, str] = {
    ViewEntity.TEMPLATES: "customtemplates",
    ViewEntity.REFERENCE_ATTRIBUTES: "attributes",
}

# Search parameters that are not grid filters, so they never become filter keys.
_NON_FILTER_PARAMS = frozenset(
    {
        # Free text and column-contains filters live on ViewQuery's own fields.
        "text",
        "name",
        "contains_field",
        "contains_text",
        "search_field",
        "search_fields",
        "search_query_string",
        # Facet lookup controls, not saved filters.
        "facet_field",
        "facet_text",
        # Sorting lives on ViewSort / ViewState.
        "order",
        "order_by",
        "sort_by",
        # Pagination state.
        "offset",
        "limit",
        "max_items",
        # Response projection.
        "additional_field",
        "source_field",
        # Nested custom-field payloads; `build_query` takes `custom_fields` instead.
        "metadata_filters",
        "custom_fields",
        # UI behavior toggles and compound payloads, not row filters.
        "collaborator_pop_up",
        "is_pop_up",
        "is_drop_down",
        "match_all_conditions",
        "details",
        "dup_detection",
        "drop_down_text",
        "drop_down_text_prop",
        "linked_to_grid",
        "composite_search",
        "project_facets",
    }
)

# Inventory-only project sub-facets, saved in the filter map as `project.*` keys.
_INVENTORY_PROJECT_FACETS = (
    "project.formulaAccess",
    "project.status",
    "project.application",
    "project.technology",
    "project.marketSegment",
    "project.location",
    "project.createdBy",
    "project.technicalLead",
    "project.program",
    "project.myRole",
)

_ENTITY_EXTRA_FILTERS: dict[ViewEntity, tuple[ViewFilter, ...]] = {
    ViewEntity.INVENTORIES: tuple(
        ViewFilter(key=key, multi=True) for key in _INVENTORY_PROJECT_FACETS
    ),
}


def _wire_key(parameter: str) -> str:
    """Map a search parameter name to its filter key (``market_segment`` -> ``marketSegment``)."""
    return re.sub(r"_([a-z0-9])", lambda m: m.group(1).upper(), parameter)


def _is_multi(annotation: Any) -> bool:
    """Return True when the annotation accepts a list, directly or in a union."""
    return typing.get_origin(annotation) is list or any(
        typing.get_origin(arg) is list for arg in typing.get_args(annotation)
    )


@cache
def grid_filters(entity: ViewEntity) -> tuple[ViewFilter, ...]:
    """Derive the filters a grid accepts from its collection's ``search`` method.

    Parameters
    ----------
    entity : ViewEntity
        The grid to list filters for.

    Returns
    -------
    tuple[ViewFilter, ...]
        The filters the grid accepts in a saved view.

    Raises
    ------
    AlbertException
        If the grid has no search-backed collection to derive filters from.
    """
    collection = _ENTITY_COLLECTIONS.get(entity)
    search = getattr(collection, "search", None) if collection is not None else None
    if search is None:
        supported = ", ".join(sorted(e.value for e in _ENTITY_COLLECTIONS))
        raise AlbertException(
            f"Filter discovery is not available for the '{entity.value}' grid. "
            f"Supported grids: {supported}."
        )
    hints = typing.get_type_hints(search)
    filters = [
        ViewFilter(
            key=_wire_key(name),
            multi=_is_multi(hints.get(name, Any)),
            parameter=name,
        )
        for name, param in inspect.signature(search).parameters.items()
        if param.kind is inspect.Parameter.KEYWORD_ONLY and name not in _NON_FILTER_PARAMS
    ]
    filters.extend(_ENTITY_EXTRA_FILTERS.get(entity, ()))
    return tuple(filters)


def grid_search_path(entity: ViewEntity) -> str:
    """Return the search route for a grid's entity.

    Parameters
    ----------
    entity : ViewEntity
        The grid to get the search route for.

    Returns
    -------
    str
        The search route (e.g. ``/api/v3/projects/search``).

    Raises
    ------
    AlbertException
        If the grid has no search-backed collection.
    """
    collection = _ENTITY_COLLECTIONS.get(entity)
    if collection is None:
        supported = ", ".join(sorted(e.value for e in _ENTITY_COLLECTIONS))
        raise AlbertException(
            f"Filter discovery is not available for the '{entity.value}' grid. "
            f"Supported grids: {supported}."
        )
    segment = _ENTITY_SEARCH_SEGMENTS.get(entity, entity.value)
    return f"/api/{collection._api_version}/{segment}/search"


def build_view_filter(
    *,
    entity: ViewEntity,
    filters: dict[str, Any],
    allow_unknown: bool = False,
) -> dict[str, Any]:
    """Validate and normalize caller filters into a saved-view filter map.

    Keys may be filter keys (``marketSegment``) or search parameter names
    (``market_segment``). ``None`` values and empty lists are dropped. Multi-value
    filters wrap scalars in a list; single-value filters reject lists and drop
    empty strings.

    Parameters
    ----------
    entity : ViewEntity
        The grid the filters apply to.
    filters : dict[str, Any]
        The caller-given filters.
    allow_unknown : bool, optional
        When True, unrecognized keys are kept as given instead of raising.

    Returns
    -------
    dict[str, Any]
        The normalized filter map, keyed by filter key.

    Raises
    ------
    ValueError
        If a key is not a known filter for the grid (and ``allow_unknown`` is
        False), or a single-value filter is given a list.
    """
    available = grid_filters(entity)
    by_key = {f.key: f for f in available}
    by_parameter = {f.parameter: f for f in available if f.parameter is not None}
    normalized: dict[str, Any] = {}
    unknown: list[str] = []
    for name, value in filters.items():
        spec = by_key.get(name) or by_parameter.get(name)
        if spec is None:
            if allow_unknown:
                normalized[name] = value
            else:
                unknown.append(name)
            continue
        if value is None:
            continue
        if spec.multi:
            values = list(value) if isinstance(value, list | tuple | set) else [value]
            if not values:
                continue
            normalized[spec.key] = values
        else:
            if isinstance(value, list | tuple | set):
                raise ValueError(f"Filter '{spec.key}' takes a single value, not a list.")
            if value == "":
                continue
            normalized[spec.key] = value
    if unknown:
        valid = ", ".join(sorted(by_key))
        raise ValueError(
            f"Unknown filter(s) for the '{entity.value}' grid: {', '.join(sorted(unknown))}. "
            f"Valid filters: {valid}. Pass `allow_unknown=True` to keep them anyway."
        )
    return normalized


def build_view_query(
    *,
    entity: ViewEntity,
    filters: dict[str, Any] | None = None,
    custom_fields: dict[str, Any] | None = None,
    search: str | None = None,
    contains: dict[str, str] | None = None,
    allow_unknown: bool = False,
) -> ViewQuery:
    """Build the query of a saved view from caller-friendly filters.

    Parameters
    ----------
    entity : ViewEntity
        The grid the query applies to.
    filters : dict[str, Any], optional
        Grid filters, keyed by filter key or search parameter name.
    custom_fields : dict[str, Any], optional
        Custom field (metadata) filters, keyed by field name. Stored under
        ``metadata.<name>`` filter keys, the same as the grid's filter bar.
    search : str, optional
        Free-text search applied on top of the filters.
    contains : dict[str, str], optional
        "Contains text" filters, keyed by column key.
    allow_unknown : bool, optional
        When True, unrecognized filter keys are kept as given instead of raising.

    Returns
    -------
    ViewQuery
        The built query.
    """
    filter_map = build_view_filter(
        entity=entity, filters=filters or {}, allow_unknown=allow_unknown
    )
    for name, value in (custom_fields or {}).items():
        if value is None:
            continue
        filter_map[f"metadata.{name}"] = value if isinstance(value, list) else [value]
    query = ViewQuery(filter=filter_map, search=search)
    if contains:
        query.contains_field = list(contains)
        query.contains_text = [str(text) for text in contains.values()]
    return query


def build_view_columns(
    *,
    defaults: list[ViewColumn],
    keep: list[str] | None = None,
    hide: list[str] | None = None,
) -> list[ViewColumn]:
    """Build a view's columns from a grid's default columns.

    Parameters
    ----------
    defaults : list[ViewColumn]
        The grid's default columns, in grid order. Not mutated.
    keep : list[str], optional
        Column IDs to keep, dropping the rest. Grid order is preserved. Cannot be
        combined with ``hide``.
    hide : list[str], optional
        Column IDs to keep but hide. Cannot be combined with ``keep``.

    Returns
    -------
    list[ViewColumn]
        The built columns.

    Raises
    ------
    ValueError
        If both ``keep`` and ``hide`` are given, or either names a column the
        grid's default view does not have.
    """
    if keep is not None and hide is not None:
        raise ValueError("Pass `keep` or `hide`, not both.")
    columns = [column.model_copy() for column in defaults]
    known = {column.id for column in columns}
    for label, ids in (("keep", keep), ("hide", hide)):
        unknown = [column_id for column_id in ids or [] if column_id not in known]
        if unknown:
            raise ValueError(
                f"Unknown column(s) in `{label}`: {', '.join(unknown)}. "
                f"Available columns: {', '.join(column.id for column in columns)}."
            )
    if keep is not None:
        kept = set(keep)
        columns = [column for column in columns if column.id in kept]
    for column in columns:
        if hide is not None and column.id in hide:
            column.is_hidden = True
    return columns


def facet_values(payload: dict[str, Any], *, key: str) -> list[FacetValue]:
    """Pull the values of one facet out of a search facet catalog.

    Parameters
    ----------
    payload : dict[str, Any]
        The search result body carrying the ``Facets`` catalog.
    key : str
        The filter key (facet parameter) to read values for.

    Returns
    -------
    list[FacetValue]
        The facet's values with their counts. Empty when the catalog has no facet
        for the key.
    """
    for raw in payload.get("Facets") or []:
        item = FacetItem.model_validate(raw)
        if item.parameter == key:
            return item.value
    return []
