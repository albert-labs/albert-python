import pytest

from albert.client import Albert
from albert.resources.btinsight import BTInsight, BTInsightCategory, BTInsightState
from albert.resources.design import DesignRunSettings, DesignRunValidationResponse
from albert.resources.smart_datasets import SmartDataset
from albert.resources.targets import (
    ComparisonOperator,
    Criterion,
    NumericRange,
)

ignore_in_ten0 = pytest.mark.xfail(
    reason="No DWH available in TEN0 test environment.",
    strict=False,
)


@ignore_in_ten0
def test_design_run_create(client: Albert, seeded_smart_dataset: SmartDataset):
    """Test triggering a design run returns a Generate BTInsight."""
    insight = client.design_runs.create(smart_dataset_id=seeded_smart_dataset.id)
    assert isinstance(insight, BTInsight)
    assert insight.id is not None
    assert insight.category == BTInsightCategory.GENERATE
    assert insight.state in {BTInsightState.QUEUED, BTInsightState.BUILDING_MODELS}


@ignore_in_ten0
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


@ignore_in_ten0
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


@ignore_in_ten0
def test_design_run_validate(client: Albert, seeded_built_smart_dataset: SmartDataset):
    """Test validating a READY smart dataset returns valid=True."""
    result = client.design_runs.validate(smart_dataset_id=seeded_built_smart_dataset.id)
    assert isinstance(result, DesignRunValidationResponse)
    assert result.valid is True
    assert result.violations == []


@ignore_in_ten0
def test_design_run_validate_with_objectives(
    client: Albert,
    seeded_built_smart_dataset: SmartDataset,
):
    """Test validating with explicit objectives returns valid=True."""
    target_id = seeded_built_smart_dataset.scope.target_ids[0]
    result = client.design_runs.validate(
        smart_dataset_id=seeded_built_smart_dataset.id,
        objectives={
            target_id: Criterion(
                operator=ComparisonOperator.BETWEEN,
                value=NumericRange(min=0, max=100),
            )
        },
    )
    assert isinstance(result, DesignRunValidationResponse)
    assert result.valid is True
