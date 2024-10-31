from albert import Albert
from albert.resources.data_templates import DataTemplate


def _list_asserts(returned_list, limit=100):
    found = False
    for i, u in enumerate(returned_list):
        found = True
        # just check the first 100
        if i == limit:
            break

        assert isinstance(u, DataTemplate)
        assert isinstance(u.name, str)
        assert isinstance(u.id, str)
        assert u.id.startswith("DAT")
    assert found


def test_basic_list(client: Albert, seeded_data_templates: list[DataTemplate]):
    data_templates = client.data_templates.list()
    _list_asserts(data_templates)


def test_get_by_name(client: Albert, seeded_data_templates: list[DataTemplate]):
    name = seeded_data_templates[0].name
    dt = client.data_templates.get_by_name(name=name)
    assert isinstance(dt, DataTemplate)
    assert dt.name == name
    assert dt.id == seeded_data_templates[0].id


def test_get_by_id(client: Albert, seeded_data_templates: list[DataTemplate]):
    dt = client.data_templates.get_by_id(id=seeded_data_templates[0].id)
    assert dt.name == seeded_data_templates[0].name
    assert dt.id == seeded_data_templates[0].id


def test_advanced_list(client: Albert, seeded_data_templates: list[DataTemplate]):
    name = seeded_data_templates[0].name
    adv_list = client.data_templates.list(name=name)
    _list_asserts(adv_list)

    adv_list_no_match = client.data_templates.list(name="chaos tags 126485% HELLO WORLD!!!!")
    assert list(adv_list_no_match) == []
