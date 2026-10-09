"""Unit tests for ``albert.collections.batch_data``."""

import json

import pytest
import requests
import responses

from albert.collections.batch_data import BatchDataCollection
from albert.exceptions import AlbertPartialError
from albert.resources.batch_data import RawCostEntry
from tests.unit.conftest import UNIT_BASE_URL

_RESYNC_URL = f"{UNIT_BASE_URL}/api/v3/batchdata/resync"


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


# --- resync request body ---


@responses.activate
def test_resync_omits_unset_formula_keys(offline_session):
    """Test that unset optional filters are omitted rather than sent as JSON null.

    The gateway validates against the OpenAPI spec, where these fields are typed
    ``string`` (not nullable), so a ``null`` would be rejected.
    """
    responses.patch(_RESYNC_URL, status=204)

    BatchDataCollection(session=offline_session).resync(
        design_id="DES100", formula_id="INV456", col_id="COL4"
    )

    body = json.loads(responses.calls[0].request.body)
    assert body == {"Formula": {"designId": "DES100", "formulaId": "INV456", "colId": "COL4"}}


@responses.activate
def test_resync_sends_set_formula_keys(offline_session):
    """Test that explicit optional filters are included in the request body."""
    responses.patch(_RESYNC_URL, status=204)

    BatchDataCollection(session=offline_session).resync(
        design_id="DES100",
        formula_id="INV456",
        col_id="COL4",
        task_id="TAS789",
        total_updated_at="2024-10-31T00:00:00.000Z",
    )

    body = json.loads(responses.calls[0].request.body)
    assert body["Formula"]["taskId"] == "TAS789"
    assert body["Formula"]["totalUpdatedAt"] == "2024-10-31T00:00:00.000Z"
