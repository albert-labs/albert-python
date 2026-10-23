import pytest
from pydantic import ValidationError

from albert.resources.lists import ListItem, ListItemCategory


@pytest.mark.parametrize(
    "category, list_type",
    [
        (None, None),
        (None, "anything"),
        (ListItemCategory.USER_DEFINED, "anything"),
        (ListItemCategory.BUSINESS_DEFINED, "anything"),
        (ListItemCategory.PROJECTS, "projectState"),
        (ListItemCategory.PROJECTS, None),
        (ListItemCategory.EXTENSIONS, "extensions"),
        (ListItemCategory.INVENTORY, "casCategory"),
        (ListItemCategory.INVENTORY, "inventoryFunction"),
    ],
)
def test_list_item_accepts_valid_list_type_for_category(category, list_type):
    """Test ListItem accepts a list_type allowed for its category, or any type when unconstrained."""
    item = ListItem(name="Option A", category=category, list_type=list_type)
    assert item.category == category
    assert item.list_type == list_type


@pytest.mark.parametrize(
    "category, list_type",
    [
        (ListItemCategory.PROJECTS, "extensions"),
        (ListItemCategory.EXTENSIONS, "projectState"),
        (ListItemCategory.INVENTORY, "projectState"),
    ],
)
def test_list_item_rejects_list_type_not_allowed_for_category(category, list_type):
    """Test ListItem rejects a list_type not allowed for its category."""
    with pytest.raises(ValidationError, match="is not allowed for category"):
        ListItem(name="Option A", category=category, list_type=list_type)


def test_list_item_wire_round_trip():
    """Test ListItem serializes to and parses back from camelCase wire format."""
    item = ListItem(
        name="In Progress",
        id="LST1",
        category=ListItemCategory.PROJECTS,
        list_type="projectState",
    )
    wire = item.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert wire == {
        "name": "In Progress",
        "albertId": "LST1",
        "category": "projects",
        "listType": "projectState",
    }
    assert ListItem.model_validate(wire) == item
