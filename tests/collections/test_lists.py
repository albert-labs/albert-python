from albert import Albert
from albert.resources.custom_fields import CustomField, FieldType
from albert.resources.lists import ListItem


def assert_valid_list_items(list_items: list[ListItem]):
    """Assert that all list items are valid ListItem instances."""
    assert list_items, "Expected at least one ListItem"
    for l in list_items:
        assert isinstance(l, ListItem)
        assert isinstance(l.name, str)
        assert isinstance(l.id, str)


def test_list_item_get_all_basic(
    client: Albert, static_lists: list[ListItem], static_custom_fields: list[CustomField]
):
    """Test list get_all using basic list_type filter."""
    list_custom_fields = [x for x in static_custom_fields if x.field_type == FieldType.LIST]
    results = list(client.lists.get_all(list_type=list_custom_fields[0].name, max_items=10))
    assert_valid_list_items(results)


def test_list_item_get_all_with_filters(client: Albert, static_lists: list[ListItem]):
    """Test list get_all with name and list_type filters."""
    first = static_lists[0]
    results = list(
        client.lists.get_all(names=[first.name], list_type=first.list_type, max_items=10)
    )
    assert_valid_list_items(results)


def test_get_by_id(client: Albert, static_lists: list[ListItem]):
    first_id = static_lists[0].id
    list_item = client.lists.get_by_id(id=first_id)
    assert isinstance(list_item, ListItem)
    assert list_item.id == first_id


def test_get_matching_id(client: Albert, static_lists: list[ListItem]):
    first = static_lists[0]
    list_item = client.lists.get_matching_item(name=first.name, list_type=first.list_type)
    assert isinstance(list_item, ListItem)
    assert list_item.id == first.id


def test_update(client: Albert, static_lists: list[ListItem], seed_prefix: str):
    updated_li = static_lists[-1]
    new_name = f"{seed_prefix} new name"
    updated_li.name = new_name
    updated_list_item = client.lists.update(list_item=updated_li)
    assert updated_list_item.name == new_name
    assert updated_list_item.id == static_lists[-1].id
