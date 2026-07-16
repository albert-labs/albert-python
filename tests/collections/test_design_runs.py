import pytest

from albert.client import Albert
from albert.exceptions import AlbertClientError
from albert.resources.btinsight import BTInsight, BTInsightCategory
from albert.resources.smart_datasets import SmartDataset
from albert.resources.targets import ComparisonOperator, Criterion


def test_design_run_create(client: Albert, seeded_smart_dataset: SmartDataset):
    """Test triggering a design run returns a Generate BTInsight."""
    insight = client.design_runs.create(smart_dataset_id=seeded_smart_dataset.id)
    assert isinstance(insight, BTInsight)
    assert insight.id is not None
    assert insight.category == BTInsightCategory.GENERATE


def test_design_run_create_with_objectives(
    client: Albert,
    seeded_smart_dataset: SmartDataset,
):
    """Test triggering a design run with explicit objectives returns a BTInsight."""
    target_id = seeded_smart_dataset.scope.target_ids[0]
    insight = client.design_runs.create(
        smart_dataset_id=seeded_smart_dataset.id,
        objectives={target_id: Criterion(operator=ComparisonOperator.GTE, value=1)},
    )
    assert isinstance(insight, BTInsight)
    assert insight.id is not None
    assert insight.category == BTInsightCategory.GENERATE


def test_design_run_create_out_of_scope_target(
    client: Albert,
    seeded_smart_dataset: SmartDataset,
):
    """Test an out-of-scope target id surfaces a client error."""
    with pytest.raises(AlbertClientError):
        client.design_runs.create(
            smart_dataset_id=seeded_smart_dataset.id,
            objectives={"TAR999999999": Criterion(operator=ComparisonOperator.GTE, value=1)},
        )
