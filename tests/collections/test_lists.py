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
