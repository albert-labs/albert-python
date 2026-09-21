import pytest

from albert.client import Albert
from albert.resources.btinsight import BTInsight, BTInsightCategory
from albert.resources.design import DesignObjective, DesignRunValidationResponse
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
    """Test create_optimization returns a Generate BTInsight with the given name."""
    target_id = seeded_smart_dataset.scope.target_ids[0]
    insight = client.design_runs.create_optimization(
        smart_dataset_id=seeded_smart_dataset.id,
        name="SDK optimization run",
        objectives={target_id: Criterion(operator="gte", value=1.0)},
    )
    assert isinstance(insight, BTInsight)
    assert insight.id is not None
    assert insight.category == BTInsightCategory.GENERATE
    assert insight.name == "SDK optimization run"


@ignore_in_ten0
def test_create_doe_returns_smart_doe_insight(
    client: Albert, seeded_smart_dataset: SmartDataset
) -> None:
    """Test create_doe returns a Smart DOE BTInsight with the given name."""
    insight = client.design_runs.create_doe(
        smart_dataset_id=seeded_smart_dataset.id,
        name="SDK space-filling run",
    )
    assert isinstance(insight, BTInsight)
    assert insight.id is not None
    assert insight.category == BTInsightCategory.SMART_DOE
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


@ignore_in_ten0
def test_create_optimization_accepts_weighted_objectives(
    client: Albert, seeded_smart_dataset: SmartDataset
) -> None:
    """Test create_optimization accepts an objective carrying a weight."""
    target_id = seeded_smart_dataset.scope.target_ids[0]
    insight = client.design_runs.create_optimization(
        smart_dataset_id=seeded_smart_dataset.id,
        name="SDK weighted optimization run",
        objectives={target_id: DesignObjective(operator="gte", value=1.0, weight=2.0)},
    )
    assert isinstance(insight, BTInsight)
    assert insight.category == BTInsightCategory.GENERATE


@ignore_in_ten0
def test_validate_optimization_accepts_weighted_objectives(
    client: Albert, seeded_smart_dataset: SmartDataset
) -> None:
    """Test validate_optimization accepts an objective carrying a weight."""
    target_id = seeded_smart_dataset.scope.target_ids[0]
    result = client.design_runs.validate_optimization(
        smart_dataset_id=seeded_smart_dataset.id,
        objectives={target_id: DesignObjective(operator="gte", value=1.0, weight=2.0)},
    )
    assert isinstance(result, DesignRunValidationResponse)


@ignore_in_ten0
def test_validate_optimization_accepts_plain_criterion(
    client: Albert, seeded_smart_dataset: SmartDataset
) -> None:
    """Test a plain Criterion is still accepted and takes the default weight."""
    target_id = seeded_smart_dataset.scope.target_ids[0]
    result = client.design_runs.validate_optimization(
        smart_dataset_id=seeded_smart_dataset.id,
        objectives={target_id: Criterion(operator="gte", value=1.0)},
    )
    assert isinstance(result, DesignRunValidationResponse)


@ignore_in_ten0
def test_validate_optimization_treats_a_null_weight_as_unweighted(
    client: Albert, seeded_smart_dataset: SmartDataset
) -> None:
    """Test an explicit null weight resolves to the default rather than failing."""
    target_id = seeded_smart_dataset.scope.target_ids[0]
    result = client.design_runs.validate_optimization(
        smart_dataset_id=seeded_smart_dataset.id,
        objectives={target_id: {"operator": "gte", "value": 1.0, "weight": None}},
    )
    assert isinstance(result, DesignRunValidationResponse)
