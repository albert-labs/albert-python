from albert import Albert
from albert.resources.base import EntityLink
from albert.resources.data_templates import DataTemplate
from albert.resources.parameter_groups import DataType, EnumValidationValue, ValueValidation
from albert.resources.tags import Tag
from albert.resources.units import Unit


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


def test_update_tags(
    client: Albert, seeded_data_templates: list[DataTemplate], seeded_tags: list[Tag]
):
    dt = seeded_data_templates[0]  # "Data Template 1"
    original_tags = [x.tag for x in dt.tags]

    new_tag = [x for x in seeded_tags if x.tag not in original_tags][0]
    dt.tags = dt.tags + [new_tag]

    updated_dt = client.data_templates.update(data_template=dt)
    assert updated_dt is not None
    assert new_tag.tag in [x.tag for x in updated_dt.tags]
    assert len(updated_dt.tags) == len(original_tags) + 1


def test_update_validations(client: Albert, seeded_data_templates: list[DataTemplate]):
    dt = seeded_data_templates[2]
    column = [
        x
        for x in dt.data_column_values
        if (len(x.validation) > 0 and x.validation[0].datatype == DataType.ENUM)
    ][0]  # Data column with enum validation
    assert column.validation[0].datatype == DataType.ENUM
    assert len(column.validation[0].value) == 2

    # Update validation
    column.validation = [ValueValidation(datatype=DataType.STRING)]
    column.value = "Updated Value"
    updated_dt = client.data_templates.update(data_template=dt)

    assert updated_dt is not None
    updated_column = updated_dt.data_column_values[0]
    assert updated_column.validation[0].datatype == DataType.STRING
    assert updated_column.value == "Updated Value"


def test_enum_validation_creation(client: Albert, seeded_data_templates: list[DataTemplate]):
    dt = seeded_data_templates[5]  # "Data Template 1"
    column = [
        x
        for x in dt.data_column_values
        if (len(x.validation) > 0 and x.validation[0].datatype == DataType.ENUM)
    ][0]  # Data column with enum validation

    assert column.validation[0].datatype == DataType.ENUM
    assert len(column.validation[0].value) == 2
    assert column.validation[0].value[0].text == "Option1"
    assert column.validation[0].value[1].text == "Option2"


def test_enum_validation_addition(client: Albert, seeded_data_templates: list[DataTemplate]):
    dt = seeded_data_templates[5]  # "Data Template 1"
    column = [
        x
        for x in dt.data_column_values
        if (len(x.validation) > 0 and x.validation[0].datatype == DataType.ENUM)
    ][0]  # Data column with enum validation

    # Add a new enum value
    column.validation[0].value.append(EnumValidationValue(text="Option3"))
    updated_dt = client.data_templates.update(data_template=dt)

    assert updated_dt is not None
    updated_column = updated_dt.data_column_values[0]
    assert len(updated_column.validation[0].value) == 3
    assert "Option3" in [x.text for x in updated_column.validation[0].value]


def test_enum_validation_update(client: Albert, seeded_data_templates: list[DataTemplate]):
    dt = seeded_data_templates[5]  # "Data Template 1"
    column = [
        x
        for x in dt.data_column_values
        if (len(x.validation) > 0 and x.validation[0].datatype == DataType.ENUM)
    ][0]  # Data column with enum validation
    old_options = [x.text for x in column.validation[0].value]
    # Replace the entire enum validation
    column.validation[0].value = [
        EnumValidationValue(text="NewOption1"),
        EnumValidationValue(text="NewOption2"),
    ]
    column.value = "NewOption1"
    updated_dt = client.data_templates.update(data_template=dt)

    assert updated_dt is not None
    updated_column = updated_dt.data_column_values[0]
    assert len(updated_column.validation[0].value) == 2
    new_options = [x.text for x in updated_column.validation[0].value]
    assert "NewOption1" in new_options
    assert "NewOption2" in new_options
    for old in old_options:
        assert old not in new_options


def test_update_units(
    client: Albert, seeded_data_templates: list[DataTemplate], seeded_units: list[Unit]
):
    dt = seeded_data_templates[3]

    column = [x for x in dt.data_column_values if x.unit is not None][0]  # Data column with unit
    original_unit = column.unit

    # Update unit
    new_unit = seeded_units[2]
    column.unit = EntityLink(id=new_unit.id)
    updated_dt = client.data_templates.update(data_template=dt)

    assert updated_dt is not None
    updated_column = [x for x in updated_dt.data_column_values if x.unit is not None][0]
    assert updated_column.unit.id == new_unit.id
    assert updated_column.unit.id != original_unit.id
