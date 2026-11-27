"""Unit tests for ``albert.collections.targets``.

``get_by_ids`` chunking is covered with ``responses`` since these tests only
assert on the requests the SDK sends.
"""

from urllib.parse import parse_qs, urlparse

import responses

from albert.collections.targets import TargetCollection
from tests.unit.conftest import UNIT_BASE_URL

_IDS_URL = f"{UNIT_BASE_URL}/api/v3/targets/ids"


def _sent_id_batches() -> list[list[str]]:
    return [parse_qs(urlparse(call.request.url).query)["id"] for call in responses.calls]


@responses.activate
def test_get_by_ids_chunks_ids_into_groups_of_300(offline_session) -> None:
    """Test that an ID list longer than 300 is split into lookups of at most 300 IDs."""
    responses.get(_IDS_URL, json={"Items": []})
    ids = [f"TAR{i}" for i in range(650)]

    result = TargetCollection(session=offline_session).get_by_ids(ids=ids)

    assert result == []
    assert _sent_id_batches() == [ids[:300], ids[300:600], ids[600:]]


@responses.activate
def test_get_by_ids_sends_one_lookup_at_chunk_boundary(offline_session) -> None:
    """Test that exactly 300 IDs are looked up in a single call."""
    responses.get(_IDS_URL, json={"Items": []})
    ids = [f"TAR{i}" for i in range(300)]

    TargetCollection(session=offline_session).get_by_ids(ids=ids)

    assert _sent_id_batches() == [ids]


@responses.activate
def test_get_by_ids_sends_no_lookup_for_empty_ids(offline_session) -> None:
    """Test that an empty ID list returns an empty result without any lookup."""
    result = TargetCollection(session=offline_session).get_by_ids(ids=[])

    assert result == []
    assert len(responses.calls) == 0
