from albert.resources.attributes import (
    AttributeValue,
    AttributeValuesResponseItem,
)


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
