import pytest
from pydantic import ValidationError

from albert.resources.custom_fields import (
    CustomField,
    FieldCategory,
    FieldType,
    ListDefault,
    ListDefaultValue,
    NumberDefault,
    ServiceType,
    StringDefault,
)


def test_custom_field_list_type_requires_category():
    """Test that a list custom field without a category is rejected."""
    with pytest.raises(ValidationError, match="Category must be set for list fields"):
        CustomField(
            name="stage_gate",
            display_name="Stage Gate",
            field_type=FieldType.LIST,
            service=ServiceType.PROJECTS,
        )


def test_custom_field_list_type_with_category_is_accepted():
    """Test that a list custom field with a category passes validation."""
    field = CustomField(
        name="stage_gate",
        display_name="Stage Gate",
        field_type=FieldType.LIST,
        service=ServiceType.PROJECTS,
        category=FieldCategory.BUSINESS_DEFINED,
    )
    assert field.category is FieldCategory.BUSINESS_DEFINED


def test_custom_field_non_list_type_does_not_require_category():
    """Test that a non-list custom field is accepted without a category."""
    field = CustomField(
        name="notes_field",
        display_name="Notes Field",
        field_type=FieldType.STRING,
        service=ServiceType.PROJECTS,
    )
    assert field.category is None


def test_custom_field_default_with_explicit_type_passes_through():
    """Test that a default payload already carrying 'type' is not modified."""
    field = CustomField(
        name="count_field",
        display_name="Count Field",
        field_type=FieldType.NUMBER,
        service=ServiceType.PROJECTS,
        default={"type": "number", "value": 3},
    )
    assert isinstance(field.default, NumberDefault)
    assert field.default.value == 3


def test_custom_field_default_none_stays_none():
    """Test that an unset default remains None instead of raising."""
    field = CustomField(
        name="count_field",
        display_name="Count Field",
        field_type=FieldType.NUMBER,
        service=ServiceType.PROJECTS,
        default=None,
    )
    assert field.default is None


def test_custom_field_default_already_typed_instance_passes_through():
    """Test that an already-constructed Default instance is not re-wrapped."""
    field = CustomField(
        name="count_field",
        display_name="Count Field",
        field_type=FieldType.NUMBER,
        service=ServiceType.PROJECTS,
        default=NumberDefault(value=7),
    )
    assert isinstance(field.default, NumberDefault)
    assert field.default.value == 7


@pytest.mark.parametrize(
    ("raw_value", "expected_type", "expected_value"),
    [
        ("hello", StringDefault, "hello"),
        (3.5, NumberDefault, 3.5),
    ],
)
def test_custom_field_default_infers_type_from_scalar_value(
    raw_value, expected_type, expected_value
):
    """Test that a default dict without 'type' infers string/number type from its value."""
    field = CustomField(
        name="f",
        display_name="F",
        field_type=FieldType.STRING,
        service=ServiceType.PROJECTS,
        default={"value": raw_value},
    )
    assert isinstance(field.default, expected_type)
    assert field.default.value == expected_value


def test_custom_field_default_infers_list_type_from_dict_value():
    """Test that a default dict with a value shaped like a list item infers FieldType.LIST."""
    field = CustomField(
        name="f",
        display_name="F",
        field_type=FieldType.LIST,
        service=ServiceType.PROJECTS,
        category=FieldCategory.BUSINESS_DEFINED,
        default={"value": {"albertId": "LST1", "name": "Option A"}},
    )
    assert isinstance(field.default, ListDefault)
    assert field.default.value == ListDefaultValue(id="LST1", name="Option A")


def test_custom_field_default_infers_list_type_from_list_value():
    """Test that a default dict with a list value infers FieldType.LIST for multiselect."""
    field = CustomField(
        name="f",
        display_name="F",
        field_type=FieldType.LIST,
        service=ServiceType.PROJECTS,
        category=FieldCategory.BUSINESS_DEFINED,
        default={"value": [{"albertId": "LST1", "name": "Option A"}]},
    )
    assert isinstance(field.default, ListDefault)
    assert field.default.value == [ListDefaultValue(id="LST1", name="Option A")]


def test_custom_field_default_uninferrable_value_raises():
    """Test that a default dict with a value of an unrecognized shape raises."""
    with pytest.raises(ValidationError, match="Cannot infer default type from value"):
        CustomField(
            name="f",
            display_name="F",
            field_type=FieldType.STRING,
            service=ServiceType.PROJECTS,
            default={"value": object()},
        )


def test_custom_field_wire_format_round_trip():
    """Test that a CustomField round-trips through wire-format dump and model_validate."""
    field = CustomField(
        name="stage_gate",
        display_name="Stage Gate",
        field_type=FieldType.LIST,
        service=ServiceType.PROJECTS,
        category=FieldCategory.BUSINESS_DEFINED,
        min=1,
        max=1,
    )
    dumped = field.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped["type"] == "list"
    assert dumped["labelName"] == "Stage Gate"
    assert "id" not in dumped

    parsed = CustomField.model_validate(dumped)
    assert parsed.field_type is FieldType.LIST
    assert parsed.display_name == "Stage Gate"
    assert parsed.category is FieldCategory.BUSINESS_DEFINED
