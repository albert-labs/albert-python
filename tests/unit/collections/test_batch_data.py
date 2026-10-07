"""Unit tests for the pure helpers of ``albert.collections.batch_data``."""

import json

import pytest
import requests

from albert.collections.batch_data import BatchDataCollection
from albert.exceptions import AlbertPartialError
from albert.resources.batch_data import RawCostEntry


def _make_response(status_code: int, body) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(body).encode()
    return response


# --- _build_raw_cost_payload ---


def test_build_raw_cost_payload_nests_product_and_maps_parent_id():
    """Test that each entry is nested under Product with the task as parentId."""
    entries = [RawCostEntry(task_id="TAS123", product_id="INV456", lot_id="LOT789")]

    payload = BatchDataCollection._build_raw_cost_payload(entries)

    assert payload == [{"parentId": "TAS123", "Product": {"id": "INV456", "lotId": "LOT789"}}]


def test_build_raw_cost_payload_omits_updated_at_when_unset():
    """Test that an unset concurrency timestamp is left out of the payload."""
    entries = [RawCostEntry(task_id="TAS123", product_id="INV456", lot_id="LOT789")]

    payload = BatchDataCollection._build_raw_cost_payload(entries)

    assert "updatedAt" not in payload[0]


def test_build_raw_cost_payload_includes_updated_at_when_set():
    """Test that an explicit concurrency timestamp is sent."""
    entries = [
        RawCostEntry(
            task_id="TAS123",
            product_id="INV456",
            lot_id="LOT789",
            updated_at="2024-10-31T00:00:00.000Z",
        )
    ]

    payload = BatchDataCollection._build_raw_cost_payload(entries)

    assert payload[0]["updatedAt"] == "2024-10-31T00:00:00.000Z"


# --- _raise_on_partial_failure ---


@pytest.mark.parametrize("status_code", [200, 201, 204])
def test_raise_on_partial_failure_ignores_non_206(status_code):
    """Test that non-partial statuses never raise, without reading the body."""
    response = _make_response(status_code, "")

    BatchDataCollection._raise_on_partial_failure(response)


def test_raise_on_partial_failure_raises_on_failed_items_dict():
    """Test that a dict body with FailedItems raises AlbertPartialError."""
    failed = [{"Id": {"rowId": "ROW1"}, "error": {"message": "boom"}}]
    response = _make_response(206, {"FailedItems": failed})

    with pytest.raises(AlbertPartialError) as excinfo:
        BatchDataCollection._raise_on_partial_failure(response)

    assert excinfo.value.failed_items == failed


def test_raise_on_partial_failure_raises_on_bare_list_body():
    """Test that a bare failure list body raises AlbertPartialError."""
    failed = [{"reason": "Failed", "params": {"parentId": "TAS123"}}]
    response = _make_response(206, failed)

    with pytest.raises(AlbertPartialError) as excinfo:
        BatchDataCollection._raise_on_partial_failure(response)

    assert excinfo.value.failed_items == failed


def test_raise_on_partial_failure_passes_on_empty_failed_items():
    """Test that a 206 with no failed items does not raise."""
    response = _make_response(206, {"FailedItems": []})

    BatchDataCollection._raise_on_partial_failure(response)
