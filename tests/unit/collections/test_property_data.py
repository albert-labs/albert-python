"""Unit tests for PropertyDataCollection payload builders and response unpacking.

Allowed under the payload-assembly rule in AGENTS.md: these guard what the SDK
sends for bulk custom-property registration and how it parses the result.
"""

import json

import pytest
import requests

from albert.collections.property_data import PropertyDataCollection
from albert.exceptions import AlbertPartialError
from albert.resources.property_data import InventoryDataColumn


def _make_response(status_code: int, body) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(body).encode()
    return response


def test_custom_bulk_add_payload_maps_each_property() -> None:
    """Test that each property becomes one add entry carrying its lot, column, and value."""
    payload = PropertyDataCollection._generate_custom_bulk_add_payload(
        inventory_id="INVA1",
        lot_id="LOT1",
        properties=[
            InventoryDataColumn(data_column_id="DAC1", value="1.2"),
            InventoryDataColumn(data_column_id="DAC2", value="3.4"),
        ],
    )

    assert payload == {
        "parentId": "INVA1",
        "Data": [
            {"operation": "add", "lotId": "LOT1", "DataColumn": [{"id": "DAC1", "value": "1.2"}]},
            {"operation": "add", "lotId": "LOT1", "DataColumn": [{"id": "DAC2", "value": "3.4"}]},
        ],
    }


def test_custom_bulk_add_payload_omits_unset_value() -> None:
    """Test that a property without a value sends no value key."""
    payload = PropertyDataCollection._generate_custom_bulk_add_payload(
        inventory_id="INVA1",
        lot_id="LOT1",
        properties=[InventoryDataColumn(data_column_id="DAC1")],
    )

    assert payload["Data"][0]["DataColumn"] == [{"id": "DAC1"}]


def test_custom_bulk_add_payload_empty_properties() -> None:
    """Test that an empty property list yields an empty Data list."""
    payload = PropertyDataCollection._generate_custom_bulk_add_payload(
        inventory_id="INVA1", lot_id="LOT1", properties=[]
    )

    assert payload == {"parentId": "INVA1", "Data": []}


# ---------------------------------------------------------------------------
# _unpack_custom_bulk_response
# ---------------------------------------------------------------------------


def test_unpack_custom_bulk_response_parses_bare_list() -> None:
    """Test that a full success returns one entry per property, in order."""
    response = _make_response(
        201,
        [
            {"DataColumn": [{"id": "DAC1", "value": "1.2"}]},
            {"DataColumn": [{"id": "DAC2", "value": "3.4"}]},
        ],
    )

    result = PropertyDataCollection._unpack_custom_bulk_response(
        response=response, inventory_id="INVA1"
    )

    assert [entry.inventory_id for entry in result] == ["INVA1", "INVA1"]
    assert [entry.data_columns[0].data_column_id for entry in result] == ["DAC1", "DAC2"]
    assert [entry.data_columns[0].value for entry in result] == ["1.2", "3.4"]


def test_unpack_custom_bulk_response_empty_bare_list() -> None:
    """Test that a full success with no entries returns an empty list."""
    response = _make_response(201, [])

    assert (
        PropertyDataCollection._unpack_custom_bulk_response(
            response=response, inventory_id="INVA1"
        )
        == []
    )


def test_unpack_custom_bulk_response_partial_error_carries_items() -> None:
    """Test that a partial success raises with the registered and rejected entries."""
    response = _make_response(
        206,
        {
            "status": "Partial Success",
            "message": "Property Data Row generation error. Partial Failure.",
            "SuccessItems": [{"DataColumn": [{"id": "DAC1", "value": "1.2"}]}],
            "FailedItems": [{"DataColumn": [{"id": "DAC2"}], "message": "Missing value"}],
        },
    )

    with pytest.raises(AlbertPartialError) as exc_info:
        PropertyDataCollection._unpack_custom_bulk_response(
            response=response, inventory_id="INVA1"
        )

    assert exc_info.value.created_items == [{"DataColumn": [{"id": "DAC1", "value": "1.2"}]}]
    assert exc_info.value.failed_items == [
        {"DataColumn": [{"id": "DAC2"}], "message": "Missing value"}
    ]
    assert "1 item(s) failed" in str(exc_info.value)
