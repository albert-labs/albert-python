"""Unit tests for the pure view-state builders in `albert.utils.views`."""

import pytest

from albert.exceptions import AlbertException
from albert.resources.views import ViewColumn, ViewEntity
from albert.utils.views import (
    build_view_columns,
    build_view_filter,
    build_view_query,
    facet_values,
    grid_filters,
    grid_search_path,
)

PROJECT_FILTERS = {
    ("status", True),
    ("marketSegment", True),
    ("application", True),
    ("technology", True),
    ("createdBy", True),
    ("location", True),
    ("program", True),
    ("technicalLead", True),
    ("fromCreatedAt", False),
    ("toCreatedAt", False),
    ("updatedBy", True),
    ("fromUpdatedAt", False),
    ("toUpdatedAt", False),
    ("linkedTo", False),
    ("myProject", False),
    ("myRole", True),
    ("formulaAccess", True),
}

TASK_FILTERS = {
    ("tags", True),
    ("taskId", True),
    ("linkedTask", True),
    ("category", True),
    ("albertId", True),
    ("dataTemplate", True),
    ("assignedTo", True),
    ("assignedToId", True),
    ("location", True),
    ("priority", True),
    ("status", True),
    ("parameterGroup", True),
    ("createdBy", True),
    ("projectId", False),
    ("fromCreatedAt", False),
    ("toCreatedAt", False),
    ("updatedBy", True),
    ("fromUpdatedAt", False),
    ("toUpdatedAt", False),
    ("dueDateDuration", False),
    ("hasAttachment", True),
    ("hasNotes", True),
    ("linkedTo", True),
    ("witnessStatus", True),
}


def _defaults() -> list[ViewColumn]:
    return [
        ViewColumn(id="albertId", width=350),
        ViewColumn(id="status"),
        ViewColumn(id="location"),
    ]


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        (ViewEntity.PROJECTS, PROJECT_FILTERS),
        (ViewEntity.TASKS, TASK_FILTERS),
    ],
)
def test_grid_filters_match_search_signatures(
    entity: ViewEntity, expected: set[tuple[str, bool]]
) -> None:
    """Test that grid filters are derived from the collection search signatures."""
    assert {(f.key, f.multi) for f in grid_filters(entity)} == expected


def test_grid_filters_expose_search_parameter_names() -> None:
    """Test that each derived filter names the search parameter it mirrors."""
    filters = {f.key: f for f in grid_filters(ViewEntity.PROJECTS)}
    assert filters["marketSegment"].parameter == "market_segment"


def test_grid_filters_inventory_adds_project_sub_facets() -> None:
    """Test that the inventory grid also accepts `project.*` sub-facet filters."""
    keys = {f.key for f in grid_filters(ViewEntity.INVENTORIES)}
    assert {"project.status", "project.location", "project.myRole"} <= keys


def test_grid_filters_unsupported_grid_raises() -> None:
    """Test that grids without a search-backed collection raise a clear error."""
    with pytest.raises(AlbertException, match="not available"):
        grid_filters(ViewEntity.UNITS)


def test_build_view_filter_accepts_keys_and_parameter_names() -> None:
    """Test that filter keys and search parameter names normalize to the same map."""
    by_key = build_view_filter(entity=ViewEntity.PROJECTS, filters={"marketSegment": ["IND"]})
    by_parameter = build_view_filter(
        entity=ViewEntity.PROJECTS, filters={"market_segment": ["IND"]}
    )
    assert by_key == by_parameter == {"marketSegment": ["IND"]}


def test_build_view_filter_wraps_scalars_for_multi_value_filters() -> None:
    """Test that a scalar value for a multi-value filter is wrapped in a list."""
    assert build_view_filter(entity=ViewEntity.PROJECTS, filters={"status": "Active"}) == {
        "status": ["Active"]
    }


def test_build_view_filter_drops_unset_values() -> None:
    """Test that None values and empty lists are dropped from the filter map."""
    assert (
        build_view_filter(entity=ViewEntity.PROJECTS, filters={"status": None, "location": []})
        == {}
    )


def test_build_view_filter_single_value_rejects_lists() -> None:
    """Test that a single-value filter rejects a list of values."""
    with pytest.raises(ValueError, match="single value"):
        build_view_filter(
            entity=ViewEntity.TASKS, filters={"due_date_duration": ["Today", "Later"]}
        )


def test_build_view_filter_single_value_drops_empty_string() -> None:
    """Test that a single-value filter drops an empty selection."""
    assert build_view_filter(entity=ViewEntity.TASKS, filters={"due_date_duration": ""}) == {}


def test_build_view_filter_unknown_key_raises_with_valid_keys() -> None:
    """Test that an unknown filter key raises and names the valid filters."""
    with pytest.raises(ValueError, match=r"Unknown filter\(s\).*statsu.*status"):
        build_view_filter(entity=ViewEntity.PROJECTS, filters={"statsu": ["Active"]})


def test_build_view_filter_allow_unknown_passes_through() -> None:
    """Test that allow_unknown keeps unrecognized keys as given."""
    assert build_view_filter(
        entity=ViewEntity.PROJECTS, filters={"statsu": ["Active"]}, allow_unknown=True
    ) == {"statsu": ["Active"]}


def test_build_view_filter_accepts_inventory_project_sub_facets() -> None:
    """Test that inventory `project.*` filters validate and keep their dotted keys."""
    assert build_view_filter(
        entity=ViewEntity.INVENTORIES, filters={"project.status": ["Active"]}
    ) == {"project.status": ["Active"]}


def test_build_view_query_combines_filters_search_and_contains() -> None:
    """Test that filters, custom fields, search text, and contains build one query."""
    query = build_view_query(
        entity=ViewEntity.PROJECTS,
        filters={"status": ["Active"]},
        custom_fields={"Program": "Battery"},
        search="coating",
        contains={"description": "polymer"},
    )
    assert query.model_dump(by_alias=True, exclude_none=True) == {
        "filter": {"status": ["Active"], "metadata.Program": ["Battery"]},
        "search": "coating",
        "containsField": ["description"],
        "containsText": ["polymer"],
    }


def test_build_view_query_empty_is_an_empty_filter() -> None:
    """Test that no inputs build a query with an empty filter map."""
    query = build_view_query(entity=ViewEntity.PROJECTS)
    assert query.filter == {}
    assert query.search is None
    assert query.contains_field is None
    assert query.contains_text is None


def test_build_view_columns_hide_marks_columns_hidden() -> None:
    """Test that hide keeps every column and marks the named ones hidden."""
    columns = build_view_columns(defaults=_defaults(), hide=["location"])
    assert [(c.id, c.is_hidden) for c in columns] == [
        ("albertId", False),
        ("status", False),
        ("location", True),
    ]


def test_build_view_columns_keep_preserves_grid_order() -> None:
    """Test that keep drops unlisted columns and preserves grid order."""
    columns = build_view_columns(defaults=_defaults(), keep=["location", "albertId"])
    assert [c.id for c in columns] == ["albertId", "location"]
    assert columns[0].width == 350


def test_build_view_columns_does_not_mutate_defaults() -> None:
    """Test that the given default columns are left unchanged."""
    defaults = _defaults()
    build_view_columns(defaults=defaults, hide=["status"])
    assert [c.is_hidden for c in defaults] == [False, False, False]


def test_build_view_columns_rejects_keep_and_hide_together() -> None:
    """Test that keep and hide cannot be combined."""
    with pytest.raises(ValueError, match="not both"):
        build_view_columns(defaults=_defaults(), keep=["status"], hide=["location"])


@pytest.mark.parametrize("argument", ["keep", "hide"])
def test_build_view_columns_unknown_column_raises(argument: str) -> None:
    """Test that naming a column outside the grid's default view raises."""
    with pytest.raises(ValueError, match="Unknown column.*bogus"):
        build_view_columns(defaults=_defaults(), **{argument: ["bogus"]})


def test_grid_search_path_uses_collection_routes() -> None:
    """Test that search routes follow the collections, not the entity names."""
    assert grid_search_path(ViewEntity.PROJECTS) == "/api/v3/projects/search"
    assert grid_search_path(ViewEntity.TEMPLATES) == "/api/v3/customtemplates/search"
    assert grid_search_path(ViewEntity.REFERENCE_ATTRIBUTES) == "/api/v3/attributes/search"


def test_facet_values_picks_the_matching_facet() -> None:
    """Test that only the values of the requested facet are returned."""
    payload = {
        "Facets": [
            {
                "name": "Status",
                "parameter": "status",
                "type": "text",
                "Value": [{"name": "Active", "count": 12}],
            },
            {
                "name": "Location",
                "parameter": "location",
                "type": "text",
                "Value": [{"name": "San Diego", "count": 3}],
            },
        ]
    }
    values = facet_values(payload, key="location")
    assert [(v.name, v.count) for v in values] == [("San Diego", 3)]


@pytest.mark.parametrize("payload", [{}, {"Facets": []}, {"Facets": None}])
def test_facet_values_missing_facet_is_empty(payload: dict) -> None:
    """Test that a catalog without the requested facet yields no values."""
    assert facet_values(payload, key="location") == []
