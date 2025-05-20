from albert import Albert
from albert.resources.custom_fields import CustomField, FieldType
from albert.resources.lists import ListItem


def _list_asserts(list_items: list[ListItem]):
    found = False
    for l in list_items:
        assert isinstance(l, ListItem)
        assert isinstance(l.name, str)
        assert isinstance(l.id, str)
        found = True
    assert found


def test_basic_list(
    client: Albert, static_lists: list[ListItem], static_custom_fields: list[CustomField]
):
    list_custom_fields = [x for x in static_custom_fields if x.field_type == FieldType.LIST]

    list_items = client.lists.list(list_type=list_custom_fields[0].name)
    _list_asserts(list_items)


def test_advanced_list(client: Albert, static_lists: list[ListItem]):
    first_name = static_lists[0].name
    first_type = static_lists[0].list_type
    list_items = client.lists.list(names=[first_name], list_type=first_type)
    _list_asserts(list_items)


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
