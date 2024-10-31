import uuid

import pytest

from albert import Albert
from albert.resources.btinsight import BTInsight, BTInsightRegistry


@pytest.fixture
def insight(client: Albert) -> BTInsight:
    # api-btinsight does not have working list/delete functionality,
    # so we need to hard-code an existing resource to play with
    return client.btinsights.get_by_id(id="INS10")


def test_update(client: Albert, insight: BTInsight):
    marker = f"TEST - {uuid.uuid4()}"
    insight.output_key = marker
    insight.start_time = marker
    insight.end_time = marker
    insight.total_time = marker
    insight.registry = BTInsightRegistry(build_logs={"status": marker})

    updated_insight = client.btinsights.update(insight=insight)
    assert updated_insight.output_key == insight.output_key
    assert updated_insight.start_time == insight.start_time
    assert updated_insight.end_time == insight.end_time
    assert updated_insight.total_time == insight.total_time
    assert updated_insight.registry == insight.registry
