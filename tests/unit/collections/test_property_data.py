"""Unit tests for PropertyDataCollection payload builders.

Allowed under the payload-assembly rule in AGENTS.md: these guard what the SDK
sends for bulk custom-property registration, with no I/O to fake.
"""

from albert.collections.property_data import PropertyDataCollection
from albert.resources.property_data import InventoryDataColumn


def test_custom_bulk_add_payload_maps_each_property() -> None:
    """Test that each property becomes one add entry carrying its column and value."""
    payload = PropertyDataCollection._generate_custom_bulk_add_payload(
        inventory_id="INVA1",
        properties=[
            InventoryDataColumn(data_column_id="DAC1", value="1.2"),
            InventoryDataColumn(data_column_id="DAC2", value="3.4"),
        ],
    )

    assert payload == {
        "parentId": "INVA1",
        "Data": [
            {"operation": "add", "DataColumn": [{"id": "DAC1", "value": "1.2"}]},
            {"operation": "add", "DataColumn": [{"id": "DAC2", "value": "3.4"}]},
        ],
    }


def test_custom_bulk_add_payload_omits_unset_value() -> None:
    """Test that a property without a value sends no value key."""
    payload = PropertyDataCollection._generate_custom_bulk_add_payload(
        inventory_id="INVA1",
        properties=[InventoryDataColumn(data_column_id="DAC1")],
    )

    assert payload["Data"][0]["DataColumn"] == [{"id": "DAC1"}]


def test_custom_bulk_add_payload_empty_properties() -> None:
    """Test that an empty property list yields an empty Data list."""
    payload = PropertyDataCollection._generate_custom_bulk_add_payload(
        inventory_id="INVA1", properties=[]
    )

    assert payload == {"parentId": "INVA1", "Data": []}
