from albert import Albert
from albert.resources.btinsight import BTInsight, BTInsightCategory, BTInsightRegistry


def test_get_by_id(client: Albert, seeded_btinsight: BTInsight):
    fetched_insight = client.btinsights.get_by_id(id=seeded_btinsight.id)
    assert fetched_insight.id == seeded_btinsight.id


def test_search_by_category(client: Albert, seeded_btinsight: BTInsight):
    results = list(
        client.btinsights.search(
            category=BTInsightCategory.CUSTOM_OPTIMIZER,
            max_items=5,
            offset=0,
        )
    )
    assert results, "No results returned for CUSTOM_OPTIMIZER category"
    for insight in results:
        assert insight.category == BTInsightCategory.CUSTOM_OPTIMIZER


def test_update(client: Albert, seeded_btinsight: BTInsight):
    marker = "TEST"
    seeded_btinsight.output_key = marker
    seeded_btinsight.start_time = marker
    seeded_btinsight.end_time = marker
    seeded_btinsight.total_time = marker
    seeded_btinsight.registry = BTInsightRegistry(build_logs={"status": marker})

    updated_insight = client.btinsights.update(insight=seeded_btinsight)
    assert updated_insight.output_key == seeded_btinsight.output_key
    assert updated_insight.start_time == seeded_btinsight.start_time
    assert updated_insight.end_time == seeded_btinsight.end_time
    assert updated_insight.total_time == seeded_btinsight.total_time
    assert updated_insight.registry == seeded_btinsight.registry
