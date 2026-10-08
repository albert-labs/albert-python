import pytest
from pydantic import ValidationError

from albert.resources.btinsight import BTInsight, BTInsightCategory
from albert.resources.btmodel import BTModel
from albert.resources.design import DesignObjective, DesignRunValidationResponse
from albert.resources.targets import Criterion


def test_design_objective_accepts_plain_criterion_with_default_weight():
    """Test that a plain Criterion is coerced into a DesignObjective with the default weight."""
    criterion = Criterion(operator="gte", value=95)
    objective = DesignObjective.model_validate(criterion)
    assert objective.weight == 1.0
    assert objective.operator == criterion.operator
    assert objective.value == criterion.value


def test_design_objective_subclass_instance_is_not_re_dumped():
    """Test that an existing DesignObjective instance is passed through unchanged."""
    objective = DesignObjective(operator="gte", value=95, weight=3.0)
    revalidated = DesignObjective.model_validate(objective)
    assert revalidated.weight == 3.0


def test_design_objective_explicit_weight_is_preserved():
    """Test that an explicitly provided weight is kept as-is."""
    objective = DesignObjective(operator="gte", value=95, weight=2.5)
    assert objective.weight == 2.5


def test_design_objective_omitted_weight_defaults_to_one():
    """Test that omitting weight defaults to 1.0."""
    objective = DesignObjective(operator="gte", value=95)
    assert objective.weight == 1.0


def test_design_objective_null_weight_is_treated_as_unweighted():
    """Test that an explicit null weight is coerced to 1.0 rather than left None."""
    objective = DesignObjective(operator="gte", value=95, weight=None)
    assert objective.weight == 1.0


@pytest.mark.parametrize("bad_weight", [0, -1.0])
def test_design_objective_non_positive_weight_rejected(bad_weight):
    """Test that a zero or negative weight fails validation."""
    with pytest.raises(ValidationError):
        DesignObjective(operator="gte", value=95, weight=bad_weight)


def test_validation_response_parses_objectives_and_metrics():
    """The public validate response parses resolved objectives and per-target metrics."""
    response = DesignRunValidationResponse.model_validate(
        {
            "valid": True,
            "violations": [],
            "targetSampleCounts": {"TAR1": 12},
            "objectives": [
                {
                    "targetId": "TAR1",
                    "targetName": "Tensile strength",
                    "dataColumnId": "DAC1",
                    "unitId": "UNI1",
                    "criterion": {"operator": "gte", "value": 10.0},
                    "weight": 2.0,
                }
            ],
            "validationMetrics": {
                "TAR1": {
                    "rmse": {"mean": 1.5, "std": 0.2},
                    "r2": None,
                    "mae": {"mean": 1.1},
                    "numFolds": 5,
                    "numReplicates": 1,
                }
            },
        }
    )
    assert response.valid
    (objective,) = response.objectives
    assert objective.target_id == "TAR1"
    assert objective.target_name == "Tensile strength"
    assert objective.data_column_id == "DAC1"
    assert objective.unit_id == "UNI1"
    assert objective.criterion.operator == "gte"
    assert objective.weight == 2.0
    metrics = response.validation_metrics["TAR1"]
    assert metrics.rmse.mean == 1.5
    assert metrics.rmse.std == 0.2
    assert metrics.r2 is None
    assert metrics.mae.std is None
    assert metrics.num_folds == 5


def test_validation_response_without_objectives_or_metrics():
    """Older payloads (and space-filling validations) carry neither field."""
    response = DesignRunValidationResponse.model_validate({"valid": True, "violations": []})
    assert response.objectives is None
    assert response.validation_metrics is None


def test_insight_objectives_property_reads_recorded_metadata():
    """BTInsight.objectives parses the run's persisted objectives; None when absent."""
    insight = BTInsight(
        name="run",
        category=BTInsightCategory.GENERATE,
        Metadata={
            "sessionData": {},
            "objectives": [
                {
                    "targetId": "TAR1",
                    "targetName": "Tensile strength",
                    "dataColumnId": "DAC1",
                    "criterion": {"operator": "lte", "value": 3.0},
                    "weight": 1.0,
                }
            ],
        },
    )
    (objective,) = insight.objectives
    assert objective.target_id == "TAR1"
    assert objective.unit_id is None
    assert objective.criterion.value == 3.0

    bare = BTInsight(name="run", category=BTInsightCategory.GENERATE)
    assert bare.objectives is None


def test_model_objectives_property_reads_recorded_metadata():
    """BTModel.objectives parses the run's persisted objectives; None when absent."""
    model = BTModel(
        name="m",
        Metadata={
            "objectives": [
                {
                    "targetId": "TAR2",
                    "targetName": "Elastic modulus",
                    "dataColumnId": "DAC2",
                    "unitId": "UNI9",
                    "criterion": {"operator": "gte", "value": 95},
                    "weight": 3.0,
                }
            ]
        },
    )
    (objective,) = model.objectives
    assert objective.target_id == "TAR2"
    assert objective.weight == 3.0

    bare = BTModel(name="m")
    assert bare.objectives is None
