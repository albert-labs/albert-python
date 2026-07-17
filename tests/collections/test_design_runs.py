from albert.client import Albert
from albert.resources.btinsight import BTInsight, BTInsightCategory, BTInsightState
from albert.resources.design import DesignRunSettings
from albert.resources.smart_datasets import SmartDataset
from albert.resources.targets import (
    ComparisonOperator,
    Criterion,
    NumericRange,
)


def test_design_run_create(client: Albert, seeded_smart_dataset: SmartDataset):
    """Test triggering a design run returns a Generate BTInsight."""
    insight = client.design_runs.create(smart_dataset_id=seeded_smart_dataset.id)
    assert isinstance(insight, BTInsight)
    assert insight.id is not None
    assert insight.category == BTInsightCategory.GENERATE
    assert insight.state in {BTInsightState.QUEUED, BTInsightState.BUILDING_MODELS}


def test_design_run_create_with_objectives(
    client: Albert,
    seeded_smart_dataset: SmartDataset,
):
    """Test triggering a design run with explicit objectives returns a BTInsight."""
    target_id = seeded_smart_dataset.scope.target_ids[0]
    insight = client.design_runs.create(
        smart_dataset_id=seeded_smart_dataset.id,
        objectives={
            target_id: Criterion(
                operator=ComparisonOperator.BETWEEN,
                value=NumericRange(min=0, max=100),
            )
        },
    )
    assert isinstance(insight, BTInsight)
    assert insight.id is not None
    assert insight.category == BTInsightCategory.GENERATE


def test_design_run_create_with_settings(
    client: Albert,
    seeded_smart_dataset: SmartDataset,
):
    """Test triggering a design run with explicit settings returns a BTInsight."""
    insight = client.design_runs.create(
        smart_dataset_id=seeded_smart_dataset.id,
        settings=DesignRunSettings(
            num_candidates_generated=1000,
            num_candidates_selected=5,
        ),
    )
    assert isinstance(insight, BTInsight)
    assert insight.id is not None
    assert insight.category == BTInsightCategory.GENERATE
