from collections.abc import Iterator

import pytest

from albert import Albert
from albert.resources.btinsight import BTInsight, BTInsightCategory


@pytest.fixture
def seeded_insight(client: Albert) -> Iterator[BTInsight]:
    ins = BTInsight(name="Test Insight", category=BTInsightCategory.CUSTOM_OPTIMIZER, metadata={})
    ins = client.btinsights.create(insight=ins)
    yield ins
    client.btinsights.delete(id=ins.id)


def test_update(client: Albert, seeded_insight: BTInsight):
    marker = "TEST"
    seeded_insight.output_key = marker
    seeded_insight.start_time = marker
    seeded_insight.end_time = marker
    seeded_insight.total_time = marker
    seeded_insight.registry = {"BuildLogs": {"status": marker}}

    updated_insight = client.btinsights.update(insight=seeded_insight)
    assert updated_insight.output_key == seeded_insight.output_key
    assert updated_insight.start_time == seeded_insight.start_time
    assert updated_insight.end_time == seeded_insight.end_time
    assert updated_insight.total_time == seeded_insight.total_time
    assert updated_insight.registry == seeded_insight.registry


def test_update_registry(client: Albert, seeded_insight: BTInsight):
    seeded_insight.registry = {"FIRST": "VALUE"}
    updated_insight = client.btinsights.update(insight=seeded_insight)
    final_insight = client.btinsights.update_registry(
        id=updated_insight.id,
        updates={"SECOND": "VALUE"},
    )
    # Assert old registry keys are maintained after update
    assert "FIRST" in final_insight.registry
    assert "SECOND" in final_insight.registry
