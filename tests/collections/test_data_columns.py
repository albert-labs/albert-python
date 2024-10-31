from albert import Albert
from albert.resources.data_columns import DataColumn


def _list_asserts(returned_list, limit=100):
    found = False
    for i, u in enumerate(returned_list):
        found = True
        # just check the first 100
        if i == limit:
            break

        assert isinstance(u, DataColumn)
        assert isinstance(u.name, str)
        assert isinstance(u.id, str)
        assert u.id.startswith("DAC")
    assert found


def test_basic_list(client: Albert, seeded_data_columns: list[DataColumn]):
    data_columns = client.data_columns.list()
    _list_asserts(data_columns)


def test_get_by_name(client: Albert, seeded_data_columns: list[DataColumn]):
    name = seeded_data_columns[0].name
    dc = client.data_columns.get_by_name(name=name)
    assert dc.name == name
    assert dc.id == seeded_data_columns[0].id


def test_get_by_id(client: Albert, seeded_data_columns: list[DataColumn]):
    dc = client.data_columns.get_by_id(id=seeded_data_columns[0].id)
    assert dc.name == seeded_data_columns[0].name
    assert dc.id == seeded_data_columns[0].id


def test_advanced_list(client: Albert, seeded_data_columns: list[DataColumn]):
    name = seeded_data_columns[0].name
    adv_list = client.data_columns.list(name=name, exact_match=False)
    _list_asserts(adv_list)

    adv_list_no_match = client.data_columns.list(
        name="chaos tags 126485% HELLO WORLD!!!!", exact_match=True
    )
    assert next(adv_list_no_match, None) == None
