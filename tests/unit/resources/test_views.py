"""Unit tests for the View resource models' validation and wire round-trips."""

import pytest
from pydantic import ValidationError

from albert.core.shared.enums import OrderBy
from albert.resources.views import View, ViewEntity, ViewSort, ViewState

LIST_ITEM = {
    "albertId": "VEW45023",
    "status": "active",
    "parentId": "USR1",
    "name": "Test View",
    "uuid": "e8a7c7bf-7e04-53e6-aefc-e859c27adb04",
    "entity": "datatemplates",
    "state": {
        "columns": [{"id": "albertId", "isHidden": False}, {"id": "owner", "isHidden": False}],
        "query": [{"filter": {"owner": ["Jane Doe"]}}],
        "sortBy": [{"id": "createdAt", "dir": "desc"}],
    },
    "system": False,
    "Created": {"at": "2026-10-06T07:00:00.000Z", "by": "USR1", "byName": "Jane Doe"},
}


def test_view_reads_wire_payload() -> None:
    """Test that a stored view parses into typed state."""
    view = View(**LIST_ITEM)

    assert view.id == "VEW45023"
    assert view.entity is ViewEntity.DATA_TEMPLATES
    assert view.state.query[0].filter == {"owner": ["Jane Doe"]}
    assert view.state.sort_by == [ViewSort(id="createdAt", direction=OrderBy.DESCENDING)]


def test_view_id_normalizes_prefix() -> None:
    """Test that a bare view number gains the ``VEW`` prefix."""
    assert View(id="45023", name="All", entity=ViewEntity.TASKS).id == "VEW45023"


def test_view_id_rejects_other_prefix() -> None:
    """Test that an ID of another entity type is rejected."""
    with pytest.raises(ValidationError, match="Expected: VEW"):
        View(id="PRO123", name="All", entity=ViewEntity.TASKS)


def test_view_state_rejects_empty_columns() -> None:
    """Test that a layout with an empty column list is rejected."""
    with pytest.raises(ValidationError):
        ViewState(columns=[])


def test_view_state_serializes_to_wire_keys() -> None:
    """Test that the state round-trips to the wire keys the grid uses."""
    state = View(**LIST_ITEM).state

    assert state.model_dump(by_alias=True, exclude_none=True, mode="json") == {
        "columns": LIST_ITEM["state"]["columns"],
        "query": [{"filter": {"owner": ["Jane Doe"]}}],
        "sortBy": [{"id": "createdAt", "dir": "desc"}],
    }


@pytest.mark.parametrize("name", ["A", "x" * 51])
def test_view_name_rejects_out_of_range_length(name: str) -> None:
    """Test that a name shorter than 2 or longer than 50 characters is rejected."""
    with pytest.raises(ValidationError):
        View(name=name, entity=ViewEntity.TASKS)


@pytest.mark.parametrize("name", ["AB", "x" * 50])
def test_view_name_accepts_boundary_lengths(name: str) -> None:
    """Test that names of exactly 2 and 50 characters are accepted."""
    assert View(name=name, entity=ViewEntity.TASKS).name == name
