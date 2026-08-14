import pytest

from albert.client import Albert
from albert.resources.btinsight import BTInsight, BTInsightCategory
from albert.resources.design import DesignRunValidationResponse
from albert.resources.smart_datasets import SmartDataset
from albert.resources.targets import Criterion

pytestmark = pytest.mark.xdist_group("datatemplates")

ignore_in_ten0 = pytest.mark.xfail(
    reason="api-designruns is not live in the TEN0 test environment.",
    strict=False,
)


@ignore_in_ten0
def test_create_optimization_returns_generate_insight(
    client: Albert, seeded_smart_dataset: SmartDataset
) -> None:
    """Test create_optimization posts to tier-1 and returns a Generate BTInsight."""
    insight = client.design_runs.create_optimization(smart_dataset_id=seeded_smart_dataset.id)
    assert isinstance(insight, BTInsight)
    assert insight.id is not None
    assert insight.category == BTInsightCategory.GENERATE


@ignore_in_ten0
def test_create_optimization_with_objectives(
    client: Albert, seeded_smart_dataset: SmartDataset
) -> None:
    """Test create_optimization accepts scoped objectives."""
    target_id = seeded_smart_dataset.scope.target_ids[0]
    insight = client.design_runs.create_optimization(
        smart_dataset_id=seeded_smart_dataset.id,
        objectives={target_id: Criterion(operator="gte", value=1.0)},
    )
    assert isinstance(insight, BTInsight)
    assert insight.id is not None


@ignore_in_ten0
def test_create_optimization_with_name(client: Albert, seeded_smart_dataset: SmartDataset) -> None:
    """Test create_optimization names the resulting insight."""
    insight = client.design_runs.create_optimization(
        smart_dataset_id=seeded_smart_dataset.id,
        name="SDK optimization run",
    )
    assert insight.name == "SDK optimization run"


@ignore_in_ten0
def test_create_doe_with_name(client: Albert, seeded_smart_dataset: SmartDataset) -> None:
    """Test create_doe names the resulting insight."""
    insight = client.design_runs.create_doe(
        smart_dataset_id=seeded_smart_dataset.id,
        name="SDK space-filling run",
    )
    assert insight.name == "SDK space-filling run"


@ignore_in_ten0
def test_validate_optimization_returns_response(
    client: Albert, seeded_smart_dataset: SmartDataset
) -> None:
    """Test validate_optimization returns a DesignRunValidationResponse."""
    result = client.design_runs.validate_optimization(smart_dataset_id=seeded_smart_dataset.id)
    assert isinstance(result, DesignRunValidationResponse)
    assert isinstance(result.valid, bool)


@ignore_in_ten0
def test_validate_doe_returns_response(client: Albert, seeded_smart_dataset: SmartDataset) -> None:
    """Test validate_doe returns a DesignRunValidationResponse."""
    result = client.design_runs.validate_doe(smart_dataset_id=seeded_smart_dataset.id)
    assert isinstance(result, DesignRunValidationResponse)
    assert isinstance(result.valid, bool)
