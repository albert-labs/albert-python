"""Unit tests for ``albert.collections.pricings``.

``get_by_inventory_ids`` chunking is covered with ``responses`` since these
tests only assert on the requests the SDK sends.
"""

from urllib.parse import parse_qs, urlparse

import responses

from albert.collections.pricings import PricingCollection
from tests.unit.conftest import UNIT_BASE_URL

_IDS_URL = f"{UNIT_BASE_URL}/api/v3/pricings/ids"


def _sent_id_batches() -> list[list[str]]:
    return [parse_qs(urlparse(call.request.url).query)["id"] for call in responses.calls]


@responses.activate
def test_get_by_inventory_ids_chunks_ids_into_groups_of_300(offline_session) -> None:
    """Test that an ID list longer than 300 is split into lookups of at most 300 IDs."""
    responses.get(_IDS_URL, json={"total": 0, "Items": []})
    ids = [f"INVA{i}" for i in range(650)]

    result = PricingCollection(session=offline_session).get_by_inventory_ids(inventory_ids=ids)

    assert result == []
    assert _sent_id_batches() == [ids[:300], ids[300:600], ids[600:]]


@responses.activate
def test_get_by_inventory_ids_sends_one_lookup_at_chunk_boundary(offline_session) -> None:
    """Test that exactly 300 IDs are looked up in a single call."""
    responses.get(_IDS_URL, json={"total": 0, "Items": []})
    ids = [f"INVA{i}" for i in range(300)]

    PricingCollection(session=offline_session).get_by_inventory_ids(inventory_ids=ids)

    assert _sent_id_batches() == [ids]


@responses.activate
def test_get_by_inventory_ids_sends_no_lookup_for_empty_ids(offline_session) -> None:
    """Test that an empty ID list returns an empty result without any lookup."""
    result = PricingCollection(session=offline_session).get_by_inventory_ids(inventory_ids=[])

    assert result == []
    assert len(responses.calls) == 0
