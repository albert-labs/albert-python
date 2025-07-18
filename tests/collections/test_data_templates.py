from albert import Albert
from albert.core.shared.models.base import EntityLink
from albert.resources.data_columns import DataColumn
from albert.resources.data_templates import (
    DataTemplate,
    DataTemplateSearchItem,
)
from albert.resources.parameter_groups import (
    DataType,
    EnumValidationValue,
    Operator,
    ParameterValue,
    ValueValidation,
)
from albert.resources.parameters import Parameter
from albert.resources.tags import Tag
from albert.resources.units import Unit


def assert_valid_data_template_items(
    items: list[DataTemplate | DataTemplateSearchItem], expected_type: type
):
    """Assert that returned items are valid DataTemplate or SearchItem instances."""
    assert items, f"No {expected_type.__name__} items returned"
    for item in items[:10]:
        assert isinstance(item, expected_type), (
            f"Expected {expected_type.__name__}, got {type(item).__name__}"
        )
        assert isinstance(item.name, str)
        assert isinstance(item.id, str)
        assert item.id.startswith("DAT")


def test_data_template_get_all_basic(client: Albert, seeded_data_templates: list[DataTemplate]):
    """Test get_all returns hydrated DataTemplate results."""
    results = list(client.data_templates.get_all(max_items=10))
    assert_valid_data_template_items(results, DataTemplate)


def test_data_template_search_basic(client: Albert, seeded_data_templates: list[DataTemplate]):
    """Test search returns partial DataTemplateSearchItem results."""
    results = list(client.data_templates.search(max_items=10))
    assert_valid_data_template_items(results, DataTemplateSearchItem)


def test_data_template_get_by_name(client: Albert, seeded_data_templates: list[DataTemplate]):
    """Test get_by_name returns a hydrated match or None if not found."""
    name = seeded_data_templates[0].name
    expected_id = seeded_data_templates[0].id

    result = client.data_templates.get_by_name(name=name)
    assert result is not None
    assert result.name == name
    assert result.id == expected_id

    chaos_name = "thisIsNotAValidNamethisIsNotAValidNamethisIsNotAValidNamethisIsNotAValidName"
    assert client.data_templates.get_by_name(name=chaos_name) is None


def test_get_by_id(client: Albert, seeded_data_templates: list[DataTemplate]):
    """Test retrieving a data template by its ID and verifying its attributes."""
    dt = client.data_templates.get_by_id(id=seeded_data_templates[0].id)
    assert dt.name == seeded_data_templates[0].name
    assert dt.id == seeded_data_templates[0].id


def test_get_by_ids(client: Albert, seeded_data_templates: list[DataTemplate]):
    """Test retrieving multiple data templates by their IDs."""
    ids = [x.id for x in seeded_data_templates]
    dt = client.data_templates.get_by_ids(ids=ids)
    assert len(dt) == len(seeded_data_templates)
    for i, d in enumerate(dt):
        assert d.name == seeded_data_templates[i].name
        assert d.id == seeded_data_templates[i].id


def test_update_tags(
    client: Albert, seeded_data_templates: list[DataTemplate], seeded_tags: list[Tag]
):
    """Test updating tags on a data template."""
    dt = seeded_data_templates[0]  # "Data Template 1"
    original_tags = [x.tag for x in dt.tags]

    new_tag = [x for x in seeded_tags if x.tag not in original_tags][0]
    dt.tags = dt.tags + [new_tag]

    updated_dt = client.data_templates.update(data_template=dt)
    assert updated_dt is not None
    assert new_tag.tag in [x.tag for x in updated_dt.tags]
    assert len(updated_dt.tags) == len(original_tags) + 1


def test_update_validations(client: Albert, seeded_data_templates: list[DataTemplate]):
    """Test updating validations on a data template."""
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
    """Test that enum validation can be created and contains expected values."""
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
    """Test that enum validation can be added to a data template."""
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
    """Test that enum validation can be updated in a data template."""
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
    """Test updating units on a data template."""
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


def test_update_parameters_and_data_columns(
    client: Albert,
    seeded_data_templates: list[DataTemplate],
    seeded_parameters: list[Parameter],
    seeded_data_columns: list[DataColumn],
):
    """Test updating parameters and data columns in a data template."""
    # Find the Parameters Data Template
    dt = next(
        (x for x in seeded_data_templates if "Parameters Data Template" in x.name),
        None,
    )
    assert dt is not None
    # Update parameter value and validation
    assert dt.parameter_values and len(dt.parameter_values) > 0

    inital_length = len(dt.parameter_values)
    param = dt.parameter_values[0]
    param.value = "999.99"
    param.validation = [
        ValueValidation(
            datatype=DataType.NUMBER,
            min="10",
            max="1000",
            operator=Operator.BETWEEN,
        )
    ]
    # Add a new parameter with validation
    new_param = ParameterValue(
        id=seeded_parameters[1].id,  # Use a unique id for the test
        value="555.55",
        validation=[
            ValueValidation(
                datatype=DataType.NUMBER,
                min="1",
                max="999",
                operator=Operator.BETWEEN,
            )
        ],
    )
    dt.parameter_values.append(new_param)
    # Update data column value and validation
    assert dt.data_column_values and len(dt.data_column_values) > 0
    col = next(x for x in dt.data_column_values if x.data_column_id == seeded_data_columns[0].id)
    col.value = "84.0"
    col.validation = [
        ValueValidation(
            datatype=DataType.NUMBER,
            min="10",
            max="200",
            operator=Operator.BETWEEN,
        )
    ]
    # col_sequence = col.sequence

    updated_dt = client.data_templates.update(data_template=dt)

    assert updated_dt is not None
    # Check parameter update
    assert updated_dt.parameter_values[0].value == "999.99"
    assert updated_dt.parameter_values[0].validation[0].min == "10"
    assert updated_dt.parameter_values[0].validation[0].max == "1000"
    # Check new parameter addition

    assert len(updated_dt.parameter_values) == inital_length + 1
    found_new_param = [p for p in updated_dt.parameter_values if p.id == new_param.id][0]
    assert found_new_param.value == "555.55"
    assert found_new_param.validation[0].min == "1"
    assert found_new_param.validation[0].max == "999"
    # Check data column update
    updated_dc = next(
        x for x in updated_dt.data_column_values if x.data_column_id == seeded_data_columns[0].id
    )
    assert updated_dc.value == "84.0"
    assert updated_dc.validation[0].min == "10"
    assert updated_dc.validation[0].max == "200"


def test_update_enum_validations_on_data_column_and_parameter(
    client: Albert,
    seeded_data_templates: list[DataTemplate],
    seeded_data_columns: list[DataColumn],
    seeded_parameters: list[Parameter],
):
    """Test updating enum validations on a data template's data column and parameter."""
    # Find the Enum Validation Data Template
    dt = next(
        (
            x
            for x in seeded_data_templates
            if "Enum Validation Data Template With Parameter" in x.name
        ),
        None,
    )

    assert dt is not None
    # Update data column enum validation
    col = next(
        x
        for x in dt.data_column_values
        if x.validation and x.validation[0].datatype.name == "ENUM"
    )

    assert col.validation is not None and col.validation[0].datatype.name == "ENUM"
    # Add a new enum option and change an existing one
    col_enum_values = col.validation[0].value

    assert isinstance(col_enum_values, list)
    col_enum_values.append(EnumValidationValue(text="OptionC"))
    col_enum_values[1].text = "OptionB-Updated"

    # Update parameter enum validation
    param = next(
        x
        for x in dt.parameter_values
        if (x.validation and x.validation[0].datatype.name == "ENUM")
    )
    assert param.validation and param.validation[0].datatype.name == "ENUM"
    param_enum_values = param.validation[0].value
    param_enum_values[1].text = "ParamOption2-Updated"
    param.value = param_enum_values[0].text
    assert isinstance(param_enum_values, list)
    param_enum_values.append(EnumValidationValue(text="ParamOption3"))
    param.value = "ParamOption3"

    updated_dt = client.data_templates.update(data_template=dt)
    assert updated_dt is not None
    # Check data column enum update
    updated_col = next(
        x for x in updated_dt.data_column_values if x.data_column_id == seeded_data_columns[1].id
    )
    updated_col_enum_texts = [x.text for x in updated_col.validation[0].value]
    assert "OptionC" in updated_col_enum_texts
    assert "OptionB-Updated" in updated_col_enum_texts
    # Check parameter enum update
    updated_param = next(x for x in updated_dt.parameter_values if x.id == seeded_parameters[2].id)
    updated_param_enum_texts = [x.text for x in updated_param.validation[0].value]
    assert "ParamOption3" in updated_param_enum_texts
    assert "ParamOption2-Updated" in updated_param_enum_texts
    assert updated_param.value == "ParamOption3"


def test_hydrate_data_template(client: Albert):
    """Test that data templates can be hydrated correctly."""
    data_templates = client.data_templates.search(max_items=3)
    assert data_templates, "Expected at least one data_template in search results"

    for data_template in data_templates:
        hydrated = data_template.hydrate()

        # identity checks
        assert hydrated.id == data_template.id
        assert hydrated.name == data_template.name
