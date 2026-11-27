import pytest
from pydantic import ValidationError

from albert.resources.attributes import (
    Attribute,
    AttributeParameterItem,
    AttributeValue,
    AttributeValuesResponseItem,
    ExpressionType,
    FormulaMetadata,
    ValidationItem,
)
from albert.resources.parameter_groups import DataType


def test_attribute_value_locked_at_creation_round_trip():
    """Test dump and parse round-trip of locked_at_creation on AttributeValue and AttributeValuesResponseItem."""
    val = AttributeValue(
        attribute_id="ATR123",
        reference_value=1.05,
        locked_at_creation=True,
    )
    dumped = val.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert dumped["lockedAtCreation"] is True

    parsed = AttributeValue.model_validate(dumped)
    assert parsed.locked_at_creation is True

    raw_item = {
        "albertId": "ATR123",
        "referenceValue": 1.05,
        "lockedAtCreation": True,
        "attributeDefinition": {
            "name": "Density",
            "fullName": "Density (g/mL)",
            "datacolumn": {"id": "DTC123", "name": "Density"},
            "category": "Property",
            "workflow": {"id": "WFL123"},
            "validation": [],
            "prmCount": 0,
        },
    }
    resp_item = AttributeValuesResponseItem.model_validate(raw_item)
    assert resp_item.locked_at_creation is True
    dumped_resp = resp_item.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert dumped_resp["lockedAtCreation"] is True


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("number", DataType.NUMBER),
        ("NUMBER", DataType.NUMBER),
        ("Enum", DataType.ENUM),
        ("string", DataType.STRING),
    ],
)
def test_validation_item_datatype_normalizes_case(raw, expected):
    """Test that ValidationItem.datatype coerces case-insensitive strings to DataType."""
    item = ValidationItem(datatype=raw)
    assert item.datatype is expected


def test_validation_item_datatype_unknown_string_coerces_to_none():
    """Test that ValidationItem.datatype tolerates an unrecognized string by coercing to None."""
    item = ValidationItem(datatype="not-a-real-type")
    assert item.datatype is None


def test_validation_item_datatype_accepts_enum_instance():
    """Test that ValidationItem.datatype accepts an already-typed DataType value unchanged."""
    item = ValidationItem(datatype=DataType.CURVE)
    assert item.datatype is DataType.CURVE


def test_validation_item_datatype_defaults_to_none_when_unset():
    """Test that ValidationItem.datatype is None when the caller never sets it."""
    item = ValidationItem()
    assert item.datatype is None


def test_validation_item_datatype_explicit_none_passes_through():
    """Test that ValidationItem.datatype passes an explicit non-string value through unchanged."""
    item = ValidationItem(datatype=None)
    assert item.datatype is None


def test_attribute_coerce_parameters_unwraps_values_key():
    """Test that Attribute.parameters unwraps a {'values': [...]} envelope from the API."""
    attr = Attribute(
        reference_name="Viscosity @ 25C",
        parameters={"values": [{"id": "PRM1", "name": "Temperature"}]},
    )
    assert attr.parameters == [AttributeParameterItem(id="PRM1", name="Temperature")]


def test_attribute_coerce_parameters_accepts_plain_list():
    """Test that Attribute.parameters accepts an already-flat list unchanged."""
    attr = Attribute(
        reference_name="Viscosity @ 25C",
        parameters=[{"id": "PRM1", "name": "Temperature"}],
    )
    assert attr.parameters == [AttributeParameterItem(id="PRM1", name="Temperature")]


def test_attribute_coerce_parameters_dict_without_values_key_fails_validation():
    """Test that a dict without a 'values' key is passed through and fails list validation."""
    with pytest.raises(ValidationError):
        Attribute(reference_name="Viscosity @ 25C", parameters={"other": []})


def test_attribute_parameters_none_when_unset():
    """Test that Attribute.parameters stays None when the caller never sets it."""
    attr = Attribute(reference_name="Viscosity @ 25C")
    assert attr.parameters is None


def test_attribute_formula_metadata_wire_round_trip():
    """Test that formulaMetadata parses into FormulaMetadata and dumps back to the same wire shape."""
    raw = {
        "albertId": "ATR1",
        "formulaMetadata": [
            {
                "displayName": "PHR",
                "expression": 'wt% / sum(wt% WHERE Function = "Resin") * 100',
                "expressionType": "INGREDIENT_BASIS",
                "requestInverse": True,
            },
            {
                "displayName": "Density",
                "expression": "harmonicMean(wt%, [ATR67])",
                "expressionType": "CALCULATED_PROPERTY",
                "requestInverse": False,
            },
        ],
    }

    attr = Attribute.model_validate(raw)

    assert attr.formula_metadata == [
        FormulaMetadata(
            display_name="PHR",
            expression='wt% / sum(wt% WHERE Function = "Resin") * 100',
            expression_type=ExpressionType.INGREDIENT_BASIS,
            request_inverse=True,
        ),
        FormulaMetadata(
            display_name="Density",
            expression="harmonicMean(wt%, [ATR67])",
            expression_type=ExpressionType.CALCULATED_PROPERTY,
            request_inverse=False,
        ),
    ]
    assert attr.model_dump(by_alias=True, mode="json", exclude_none=True) == raw


def test_formula_metadata_parses_unknown_expression_type_as_str():
    """Test that an expression type the SDK does not know parses instead of raising."""
    formula = FormulaMetadata.model_validate(
        {
            "displayName": "Future",
            "expression": "sum(wt%)",
            "expressionType": "SOMETHING_NEW",
            "requestInverse": False,
        }
    )
    assert formula.expression_type == "SOMETHING_NEW"


def test_formula_metadata_keeps_undeclared_keys_on_dump():
    """Test that keys the SDK does not declare survive a parse and dump."""
    raw = {
        "displayName": "Total Solids",
        "expression": "sum(ingredient_basis)",
        "expressionType": "CALCULATED_PROPERTY",
        "requestInverse": False,
        "futureKey": "kept",
    }
    assert FormulaMetadata.model_validate(raw).model_dump(by_alias=True, mode="json") == raw
