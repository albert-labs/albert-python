from albert import Albert
from albert.resources.btinsight import BTInsight, BTInsightRegistry


def test_update(client: Albert, static_btinsight: BTInsight):
    insight = static_btinsight.model_copy()

    marker = "TEST"
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
