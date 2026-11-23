"""Unit tests for descriptor value parsing."""

import pytest
from pydantic import ValidationError

from albert.resources.descriptors import (
    BooleanDescriptorValue,
    DescriptorValue,
    IntegerDescriptorValue,
    IntegerListDescriptorValue,
    NumericDescriptorValue,
    NumericListDescriptorValue,
    StringDescriptorValue,
)


@pytest.mark.parametrize(
    ("wire", "expected"),
    [
        pytest.param(
            {"name": "MolecularWeight", "value": {"type": "numeric", "value": 46.07}},
            DescriptorValue(
                name="MolecularWeight",
                value=NumericDescriptorValue(value=46.07),
            ),
            id="numeric",
        ),
        pytest.param(
            {"name": "MACCSKeys", "value": {"type": "numeric_list", "value": [0.0, 1.0]}},
            DescriptorValue(
                name="MACCSKeys",
                value=NumericListDescriptorValue(value=[0.0, 1.0]),
            ),
            id="numeric-list",
        ),
        pytest.param(
            {"name": "NumAtoms", "value": {"type": "integer", "value": 9}},
            DescriptorValue(name="NumAtoms", value=IntegerDescriptorValue(value=9)),
            id="integer",
        ),
        pytest.param(
            {"name": "AtomCounts", "value": {"type": "integer_list", "value": [6, 1]}},
            DescriptorValue(
                name="AtomCounts",
                value=IntegerListDescriptorValue(value=[6, 1]),
            ),
            id="integer-list",
        ),
        pytest.param(
            {"name": "IsChiral", "value": {"type": "boolean", "value": False}},
            DescriptorValue(name="IsChiral", value=BooleanDescriptorValue(value=False)),
            id="boolean",
        ),
        pytest.param(
            {"name": "Formula", "value": {"type": "string", "value": "C2H6O"}},
            DescriptorValue(name="Formula", value=StringDescriptorValue(value="C2H6O")),
            id="string",
        ),
    ],
)
def test_descriptor_value_parses_each_tag(wire: dict, expected: DescriptorValue) -> None:
    """Test that each descriptor value tag parses to its model."""
    assert DescriptorValue.model_validate(wire) == expected


@pytest.mark.parametrize(
    ("tag", "model"),
    [
        ("numeric", NumericDescriptorValue),
        ("integer", IntegerDescriptorValue),
        ("boolean", BooleanDescriptorValue),
        ("string", StringDescriptorValue),
    ],
)
def test_descriptor_value_parses_a_null_scalar(tag: str, model: type) -> None:
    """Test that a null scalar parses for each scalar tag."""
    parsed = DescriptorValue.model_validate(
        {"name": "RadiusOfGyration", "value": {"type": tag, "value": None}}
    )

    assert parsed.value == model(value=None)


@pytest.mark.parametrize(
    ("tag", "value", "model"),
    [
        ("numeric_list", [1.0, None], NumericListDescriptorValue),
        ("integer_list", [1, None], IntegerListDescriptorValue),
    ],
)
def test_descriptor_value_parses_a_null_list_component(
    tag: str,
    value: list,
    model: type,
) -> None:
    """Test that a null list component parses for each list tag."""
    parsed = DescriptorValue.model_validate(
        {"name": "MACCSKeys", "value": {"type": tag, "value": value}}
    )

    assert parsed.value == model(value=value)


def test_descriptor_value_ignores_unknown_fields() -> None:
    """Test that unknown keys on a descriptor value are dropped."""
    parsed = DescriptorValue.model_validate(
        {
            "name": "MolecularWeight",
            "source": "catalog",
            "value": {"type": "numeric", "value": 46.07, "bits": 64},
        }
    )

    assert parsed == DescriptorValue(
        name="MolecularWeight",
        value=NumericDescriptorValue(value=46.07),
    )


def test_descriptor_value_rejects_an_unknown_tag() -> None:
    """Test that an unknown descriptor value tag is rejected."""
    with pytest.raises(ValidationError):
        DescriptorValue.model_validate(
            {"name": "MolecularWeight", "value": {"type": "matrix", "value": 1}}
        )
