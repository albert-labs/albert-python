from albert import Albert
from albert.resources.data_templates import DataColumn, DataColumnValue, DataTemplate


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
    assert dt is not None
    assert dt.name == name
    assert dt.id == seeded_data_templates[0].id
    chaos_name = "JHByu8gt43278hixvy87H&*(#BIuyvd)"
    dt = client.data_templates.get_by_name(name=chaos_name)
    assert dt is None


def test_get_by_id(client: Albert, seeded_data_templates: list[DataTemplate]):
    dt = client.data_templates.get_by_id(id=seeded_data_templates[0].id)
    assert dt.name == seeded_data_templates[0].name
    assert dt.id == seeded_data_templates[0].id


def test_get_by_ids(client: Albert, seeded_data_templates: list[DataTemplate]):
    ids = [x.id for x in seeded_data_templates]
    dt = client.data_templates.get_by_ids(ids=ids)
    assert len(dt) == len(seeded_data_templates)
    for i, d in enumerate(dt):
        assert d.name == seeded_data_templates[i].name
        assert d.id == seeded_data_templates[i].id


def test_advanced_list(client: Albert, seeded_data_templates: list[DataTemplate]):
    name = seeded_data_templates[0].name
    adv_list = client.data_templates.list(name=name)
    _list_asserts(adv_list)

    adv_list_no_match = client.data_templates.list(name="FAKEFAKEFAKEFAKEFAKEFAKE")
    assert next(adv_list_no_match, None) == None


def test_update(client: Albert, seeded_data_templates: list[DataTemplate], seed_prefix: str):
    dt = seeded_data_templates[0]
    new_name = f"{seed_prefix} new name"
    dt.name = new_name
    updated_dt = client.data_templates.update(data_template=dt)
    assert updated_dt.name == new_name
    assert updated_dt.id == dt.id


def test_add_data_column_value(
    client: Albert,
    seeded_data_templates: list[DataTemplate],
    seeded_data_columns: list[DataColumn],
):
    dt = seeded_data_templates[0]
    unused_column = [
        x
        for x in seeded_data_columns
        if x.id not in [x.data_column_id for x in dt.data_column_values]
    ][0]

    original_count = len(dt.data_column_values)

    new_value = DataColumnValue(
        data_column=unused_column,
        value="hello world",
    )
    updated_dt = client.data_templates.add_data_columns(
        data_template_id=dt.id, data_columns=[new_value]
    )

    assert updated_dt.name == dt.name
    assert updated_dt.id == dt.id
    assert len(updated_dt.data_column_values) == original_count + 1
