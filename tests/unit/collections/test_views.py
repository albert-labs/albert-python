"""Unit tests for ViewCollection private helpers.

Covers the pure ``_build_update_data`` change-list builder (unset / explicit
``None`` / changed / unchanged matrix) and the ``_validate_order`` reorder guard.
"""

import pytest

from albert.collections.views import ViewCollection
from albert.resources.views import View, ViewColumn, ViewEntity, ViewQuery, ViewState

EXISTING = {
    "albertId": "VEW1",
    "name": "My Data Templates",
    "entity": "datatemplates",
    "state": {
        "columns": [{"id": "albertId", "isHidden": False}, {"id": "owner", "isHidden": False}],
        "query": [{"filter": {}, "search": None}],
        "sortBy": [{"id": "createdAt", "dir": "desc"}],
        "groupBy": "owner",
    },
}


def _view(**kwargs) -> View:
    return View(id="VEW1", entity=ViewEntity.DATA_TEMPLATES, name=EXISTING["name"], **kwargs)


def test_build_update_data_no_changes_is_empty() -> None:
    """Test that a view with only identity fields set produces no changes."""
    assert ViewCollection._build_update_data(existing=EXISTING, updated=_view()) == []


def test_build_update_data_renames() -> None:
    """Test that a changed name produces a single name change carrying the stored name."""
    updated = View(id="VEW1", entity=ViewEntity.DATA_TEMPLATES, name="Mine")

    assert ViewCollection._build_update_data(existing=EXISTING, updated=updated) == [
        {
            "operation": "update",
            "attribute": "name",
            "oldValue": "My Data Templates",
            "newValue": "Mine",
        }
    ]


def test_build_update_data_partial_state_keeps_unset_parts() -> None:
    """Test that setting only the query replaces filters and keeps columns, sort, and grouping."""
    updated = _view(state=ViewState(query=[ViewQuery(filter={"owner": ["Jane Doe"]})]))

    data = ViewCollection._build_update_data(existing=EXISTING, updated=updated)

    assert data == [
        {
            "operation": "update",
            "attribute": "state",
            "oldValue": EXISTING["state"],
            "newValue": {**EXISTING["state"], "query": [{"filter": {"owner": ["Jane Doe"]}}]},
        }
    ]


def test_build_update_data_explicit_none_group_by_clears_grouping() -> None:
    """Test that an explicit ``group_by=None`` removes the stored grouping."""
    updated = _view(state=ViewState(group_by=None))

    data = ViewCollection._build_update_data(existing=EXISTING, updated=updated)

    assert data[0]["newValue"]["groupBy"] is None
    assert data[0]["newValue"]["columns"] == EXISTING["state"]["columns"]


def test_build_update_data_explicit_none_columns_is_ignored() -> None:
    """Test that an explicit ``columns=None`` keeps the stored columns (a view needs columns)."""
    updated = _view(state=ViewState(columns=None))

    assert ViewCollection._build_update_data(existing=EXISTING, updated=updated) == []


def test_build_update_data_round_tripped_state_is_unchanged() -> None:
    """Test that a fetched view sent back unchanged produces no changes."""
    fetched = View(**EXISTING)

    assert ViewCollection._build_update_data(existing=EXISTING, updated=fetched) == []


def test_build_update_data_changed_columns() -> None:
    """Test that new columns replace the stored columns."""
    updated = _view(state=ViewState(columns=[ViewColumn(id="albertId", is_hidden=True)]))

    data = ViewCollection._build_update_data(existing=EXISTING, updated=updated)

    assert data[0]["newValue"]["columns"] == [{"id": "albertId", "isHidden": True}]
    assert data[0]["oldValue"] == EXISTING["state"]


def test_build_update_data_rejects_entity_change() -> None:
    """Test that moving a view to another grid is rejected."""
    updated = View(id="VEW1", entity=ViewEntity.PROJECTS, name=EXISTING["name"])

    with pytest.raises(ValueError, match="entity cannot be changed"):
        ViewCollection._build_update_data(existing=EXISTING, updated=updated)


def test_validate_order_accepts_reordering() -> None:
    """Test that a permutation of the current order is accepted."""
    ViewCollection._validate_order(current=["VEW1", "VEW2"], new=["VEW2", "VEW1"])


@pytest.mark.parametrize(
    "new,match",
    [
        (["VEW1"], "missing"),
        (["VEW1", "VEW2", "VEW3"], "not in the current order"),
        (["VEW1", "VEW1", "VEW2"], "must not repeat"),
    ],
)
def test_validate_order_rejects_non_permutation(new: list[str], match: str) -> None:
    """Test that dropping, adding, or repeating a view is rejected."""
    with pytest.raises(ValueError, match=match):
        ViewCollection._validate_order(current=["VEW1", "VEW2"], new=new)
