"""Unit tests for the Structure resource model."""

from albert.resources.structures import Structure, StructureAttributeValue, StructureField


def test_structure_parses_wire_format():
    """Test that a structure parses from its camelCase wire shape."""
    structure = Structure(
        **{
            "id": "STT1f139757-997e-62b0-863b-4cbed10437c7",
            "smiles": "O",
            "inchiKey": "XLYOFNOQVPJJNP-UHFFFAOYSA-N",
            "iupacNames": "oxidane",
            "commonName": ["water"],
            "primaryName": "water",
            "pubchemCid": 962,
            "molecularWeight": {
                "atrId": "ATR2480",
                "value": "18.010564684",
                "unitId": "UNI33389dc7-3a92-4253-b1b4-970daaab956a",
                "unitName": "Gram Per Mole",
            },
        }
    )

    assert structure.id == "STT1f139757-997e-62b0-863b-4cbed10437c7"
    assert structure.inchi_key == "XLYOFNOQVPJJNP-UHFFFAOYSA-N"
    assert structure.common_name == ["water"]
    assert structure.pubchem_cid == 962
    assert structure.molecular_weight == StructureAttributeValue(
        attribute_id="ATR2480",
        value="18.010564684",
        unit_id="UNI33389dc7-3a92-4253-b1b4-970daaab956a",
        unit_name="Gram Per Mole",
    )


def test_structure_wire_round_trip():
    """Test that a structure serializes back to its camelCase wire shape."""
    payload = {
        "id": "STT1f139757-997e-62b0-863b-4cbed10437c7",
        "smiles": "O",
        "inchiKey": "XLYOFNOQVPJJNP-UHFFFAOYSA-N",
        "molecularWeight": {"atrId": "ATR2480", "value": 18.015, "unitName": "Gram Per Mole"},
    }

    structure = Structure(**payload)
    dumped = structure.model_dump(by_alias=True, mode="json", exclude_none=True)

    assert dumped["inchiKey"] == "XLYOFNOQVPJJNP-UHFFFAOYSA-N"
    assert dumped["molecularWeight"]["atrId"] == "ATR2480"
    assert Structure(**dumped) == structure


def test_structure_preserves_unknown_fields():
    """Test that undeclared attributes are kept on the instance instead of dropped."""
    structure = Structure(**{"smiles": "O", "boilingPoint": {"atrId": "ATR1", "value": "100"}})

    assert structure.model_extra["boilingPoint"] == {"atrId": "ATR1", "value": "100"}


def test_structure_fields_default_to_none():
    """Test that unrequested attributes parse as None."""
    structure = Structure(smiles="O")

    assert structure.id is None
    assert structure.inchi_key is None
    assert structure.molecular_weight is None
    assert structure.properties is None


def test_structure_attribute_value_accepts_numeric_and_text_values():
    """Test that attribute values accept both numeric and textual measurements."""
    numeric = StructureAttributeValue(atrId="ATR1", value=1.42)
    text = StructureAttributeValue(atrId="ATR1", value="white powder")

    assert numeric.value == 1.42
    assert text.value == "white powder"


def test_structure_field_values_match_wire_names():
    """Test that StructureField members carry their camelCase wire names."""
    assert StructureField.ID.value == "id"
    assert StructureField.INCHI_KEY.value == "inchiKey"
    assert StructureField.PUBCHEM_CID.value == "pubchemCid"
    assert StructureField.SMILES.value == "smiles"
