import uuid
from contextlib import suppress

import pytest

from albert import Albert
from albert.exceptions import NotFoundError
from albert.resources.attributes import (
    Attribute,
    AttributeCategory,
    AttributeScope,
    AttributeSearchItem,
    AttributeValue,
    AttributeValuesResponse,
    ValidationItem,
)
from albert.resources.data_columns import DataColumn
from albert.resources.inventory import InventoryItem
from albert.resources.lots import Lot
from albert.resources.parameter_groups import DataType, EnumValidationValue, Operator


def test_attribute_create(client: Albert, seeded_data_columns: list[DataColumn]):
    """Test creating an attribute and verifying the returned ID and category."""
    attribute = Attribute(
        datacolumn_id=seeded_data_columns[0].id,
        category=AttributeCategory.PROPERTY,
        validation=[ValidationItem(datatype=DataType.NUMBER)],
    )
    created = client.attributes.create(attribute=attribute)

    assert created.id is not None
    assert created.id.startswith("ATR")
    assert created.category == AttributeCategory.PROPERTY

    with suppress(NotFoundError):
        client.attributes.delete(id=created.id)


def test_attribute_get_by_id(client: Albert, seeded_attributes: list[Attribute]):
    """Test retrieving an attribute by its ID."""
    target = seeded_attributes[0]
    result = client.attributes.get_by_id(id=target.id)

    assert isinstance(result, Attribute)
    assert result.id == target.id
    assert result.category == AttributeCategory.PROPERTY


def test_attribute_get_by_ids(client: Albert, seeded_attributes: list[Attribute]):
    """Test retrieving multiple attributes by a list of IDs."""
    ids = [a.id for a in seeded_attributes]
    results = client.attributes.get_by_ids(ids=ids)

    assert len(results) == len(seeded_attributes)
    returned_ids = {r.id for r in results}
    for attr_id in ids:
        assert attr_id in returned_ids


def test_attribute_get_all(client: Albert, seeded_attributes: list[Attribute]):
    """Test listing attributes with max_items respects the limit."""
    results = list(client.attributes.get_all(max_items=5))

    assert len(results) <= 5
    for item in results:
        assert isinstance(item, Attribute)
        assert item.id is not None
        assert item.id.startswith("ATR")


def test_attribute_get_all_by_category(client: Albert, seeded_attributes: list[Attribute]):
    """Test listing attributes filtered by category."""
    results = list(client.attributes.get_all(category=AttributeCategory.PROPERTY, max_items=10))

    assert len(results) > 0
    for item in results:
        assert item.category == AttributeCategory.PROPERTY


def test_attribute_update_reference_name(client: Albert, seeded_attributes: list[Attribute]):
    """Test updating an attribute's reference name."""
    attr = client.attributes.get_by_id(id=seeded_attributes[2].id)
    new_ref_name = f"updated-ref-{uuid.uuid4().hex[:8]}"
    attr.reference_name = new_ref_name

    updated = client.attributes.update(attribute=attr)

    assert updated.reference_name == new_ref_name


def test_attribute_update_validation(client: Albert, seeded_attributes: list[Attribute]):
    """Test updating an attribute's validation rules."""
    attr = client.attributes.get_by_id(id=seeded_attributes[0].id)
    attr.validation = [
        ValidationItem(datatype=DataType.NUMBER, min=0.0, max=100.0, operator=Operator.BETWEEN)
    ]

    updated = client.attributes.update(attribute=attr)

    assert updated.validation is not None
    assert updated.validation[0].datatype == DataType.NUMBER
    assert updated.validation[0].min == 0.0
    assert updated.validation[0].max == 100.0


def test_attribute_update_enum(client: Albert, seeded_attributes: list[Attribute]):
    """Test updating enum values within an attribute's validation."""
    attr = client.attributes.get_by_id(id=seeded_attributes[1].id)
    assert attr.validation is not None
    assert attr.validation[0].datatype == DataType.ENUM

    existing_values = attr.validation[0].value
    assert isinstance(existing_values, list)

    attr.validation[0].value = [
        *existing_values,
        EnumValidationValue(text="Option3"),
    ]

    updated = client.attributes.update(attribute=attr)

    assert updated.validation is not None
    enum_texts = [v.text for v in updated.validation[0].value]
    assert "Option1" in enum_texts
    assert "Option2" in enum_texts
    assert "Option3" in enum_texts


def test_attribute_delete(client: Albert, seeded_data_columns: list[DataColumn]):
    """Test deleting an attribute removes it from the platform."""
    attribute = Attribute(
        datacolumn_id=seeded_data_columns[3].id,
        category=AttributeCategory.PROPERTY,
        validation=[ValidationItem(datatype=DataType.STRING)],
    )
    created = client.attributes.create(attribute=attribute)
    assert created.id is not None

    client.attributes.delete(id=created.id)

    with pytest.raises(NotFoundError):
        client.attributes.get_by_id(id=created.id)


def test_attribute_search(client: Albert, seeded_attributes: list[Attribute]):
    """Test searching attributes returns AttributeSearchItem results."""
    results = list(client.attributes.search(max_items=10))

    assert len(results) > 0
    for item in results:
        assert isinstance(item, AttributeSearchItem)
        assert item.id is not None
        assert item.id.startswith("ATR")


def test_attribute_search_by_text(client: Albert, seeded_attributes: list[Attribute]):
    """Test searching attributes by text returns matching results."""
    attr = seeded_attributes[1]
    assert attr.datacolumn is not None

    results = list(client.attributes.search(text=attr.datacolumn.name, max_items=10))

    assert len(results) > 0
    ids = [r.id for r in results]
    assert attr.id in ids


# --- Attribute Values ---


def test_attribute_add_values(
    client: Albert,
    seeded_attributes: list[Attribute],
    seeded_inventory: list[InventoryItem],
):
    """Test add_values sets reference values and handles duplicates without error."""
    inventory = seeded_inventory[0]
    attr = seeded_attributes[0]

    values = [AttributeValue(attributeId=attr.id, referenceValue=42.0)]
    result = client.attributes.add_values(parent_id=inventory.id, values=values)

    assert isinstance(result, AttributeValuesResponse)
    assert result.parent_id == inventory.id
    assert len(result.attributes) == 1
    assert result.attributes[0].id == attr.id
    assert result.attributes[0].reference_value == 42.0

    # Calling add_values again with the same attribute should update, not raise
    result2 = client.attributes.add_values(
        parent_id=inventory.id,
        values=[AttributeValue(attributeId=attr.id, referenceValue=99.0)],
    )
    assert result2.attributes[0].reference_value == 99.0

    client.attributes.clear_values(parent_id=inventory.id)


def test_attribute_get_values_scope_self(
    client: Albert,
    seeded_attributes: list[Attribute],
    seeded_inventory: list[InventoryItem],
):
    """Test get_values with scope=SELF returns only the parent entity's values."""
    inventory = seeded_inventory[0]
    attr = seeded_attributes[0]

    client.attributes.add_values(
        parent_id=inventory.id,
        values=[AttributeValue(attributeId=attr.id, referenceValue=10.0)],
    )

    results = list(client.attributes.get_values(parent_id=inventory.id, scope=AttributeScope.SELF))

    assert len(results) >= 1
    parent_ids = [r.parent_id for r in results]
    assert inventory.id in parent_ids

    client.attributes.clear_values(parent_id=inventory.id)


def test_attribute_get_values_scope_all(
    client: Albert,
    seeded_attributes: list[Attribute],
    seeded_inventory: list[InventoryItem],
    seeded_lots: list[Lot],
):
    """Test get_values with scope=ALL returns values for inventory and its lots."""
    inventory = seeded_inventory[0]
    lot = seeded_lots[0]
    attr = seeded_attributes[0]

    client.attributes.add_values(
        parent_id=inventory.id,
        values=[AttributeValue(attributeId=attr.id, referenceValue=5.0)],
    )
    client.attributes.add_values(
        parent_id=lot.id,
        values=[AttributeValue(attributeId=attr.id, referenceValue=7.5)],
    )

    results = list(client.attributes.get_values(parent_id=inventory.id, scope=AttributeScope.ALL))
    parent_ids = {r.parent_id for r in results}

    assert inventory.id in parent_ids
    assert lot.id in parent_ids

    client.attributes.clear_values(parent_id=inventory.id, scope=AttributeScope.ALL)


@pytest.mark.xfail(reason="GET /attributes/values bulk endpoint returns 500 — backend issue")
def test_attribute_get_bulk_values(
    client: Albert,
    seeded_attributes: list[Attribute],
    seeded_inventory: list[InventoryItem],
):
    """Test get_bulk_values returns values for multiple parent entities."""
    inv1 = seeded_inventory[0]
    inv2 = seeded_inventory[1]
    attr = seeded_attributes[0]

    client.attributes.add_values(
        parent_id=inv1.id, values=[AttributeValue(attributeId=attr.id, referenceValue=1.0)]
    )
    client.attributes.add_values(
        parent_id=inv2.id, values=[AttributeValue(attributeId=attr.id, referenceValue=2.0)]
    )

    try:
        results = client.attributes.get_bulk_values(parent_ids=[inv1.id, inv2.id])
        returned_ids = {r.parent_id for r in results}
        assert inv1.id in returned_ids
        assert inv2.id in returned_ids
    finally:
        client.attributes.clear_values(parent_id=inv1.id)
        client.attributes.clear_values(parent_id=inv2.id)


def test_attribute_delete_values(
    client: Albert,
    seeded_attributes: list[Attribute],
    seeded_inventory: list[InventoryItem],
):
    """Test delete_values removes only the specified attribute values."""
    inventory = seeded_inventory[0]
    attr0 = seeded_attributes[0]
    attr1 = seeded_attributes[2]

    client.attributes.add_values(
        parent_id=inventory.id,
        values=[
            AttributeValue(attributeId=attr0.id, referenceValue=1.0),
            AttributeValue(attributeId=attr1.id, referenceValue="hello"),
        ],
    )

    client.attributes.delete_values(parent_id=inventory.id, attribute_ids=[attr0.id])

    results = list(client.attributes.get_values(parent_id=inventory.id))
    remaining_ids = {a.id for r in results for a in r.attributes}

    assert attr0.id not in remaining_ids
    assert attr1.id in remaining_ids

    client.attributes.clear_values(parent_id=inventory.id)


def test_attribute_clear_values(
    client: Albert,
    seeded_attributes: list[Attribute],
    seeded_inventory: list[InventoryItem],
):
    """Test clear_values removes all attribute values from a parent entity."""
    inventory = seeded_inventory[0]
    attr = seeded_attributes[0]

    client.attributes.add_values(
        parent_id=inventory.id,
        values=[AttributeValue(attributeId=attr.id, referenceValue=99.0)],
    )

    client.attributes.clear_values(parent_id=inventory.id)

    results = list(client.attributes.get_values(parent_id=inventory.id))
    assert all(len(r.attributes) == 0 for r in results)
