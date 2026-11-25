"""Unit tests for ``albert.collections.targets``.

``get_by_ids`` chunking is covered with ``responses`` since these tests only
assert on the requests the SDK sends.
"""

import json
from urllib.parse import parse_qs, urlparse

import responses

from albert.collections.targets import TargetCollection
from albert.resources.targets import (
    ComparisonOperator,
    Criterion,
    Target,
    TargetType,
)
from tests.unit.conftest import UNIT_BASE_URL

_BASE_URL = f"{UNIT_BASE_URL}/api/v3/targets"
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


@responses.activate
def test_create_posts_label_id(offline_session) -> None:
    """Test that create sends labelId in the POST body when set on the target."""
    responses.post(
        _BASE_URL,
        json={
            "id": "TAR1",
            "name": "Viscosity spec",
            "type": "performance",
            "dataTemplateId": "DAT1",
            "dataColumnId": "DAC1",
            "targetValue": {"operator": "gte", "value": 90},
            "isRequired": True,
            "labelId": "LBL1",
        },
    )

    created = TargetCollection(session=offline_session).create(
        target=Target(
            name="Viscosity spec",
            type=TargetType.PERFORMANCE,
            data_template_id="DAT1",
            data_column_id="DAC1",
            target_value=Criterion(operator=ComparisonOperator.GTE, value=90),
            is_required=True,
            label_id="LBL1",
        )
    )

    assert created.id == "TAR1"
    assert created.label_id == "LBL1"
    assert responses.calls[0].request.body is not None
    body = json.loads(responses.calls[0].request.body)
    assert body["labelId"] == "LBL1"
