import pytest
from pydantic import ValidationError

from albert.resources.design import (
    DesignObjective,
    DesignRunValidationResponse,
    DesignRunViolation,
    DesignRunViolationCode,
)
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


@pytest.mark.parametrize(
    "code",
    [
        "estimator_downgraded",
        "variable_not_derived",
        "target_not_in_dataset",
        "transform_requires_positive_target",
        "inert_mask_entry",
        "feature_dropped_by_overlap",
        "duplicate_extra",
        "conflicting_label_definition",
    ],
)
def test_run_violation_parses_the_model_config_codes_a_run_can_report(code):
    """Test that a stored-config warning on a valid run parses to the enum."""
    result = DesignRunValidationResponse.model_validate(
        {
            "valid": True,
            "violations": [{"code": code, "message": "m", "components": ["outputs/TAR1"]}],
        }
    )

    assert isinstance(result.violations[0].code, DesignRunViolationCode)
    assert result.violations[0].components == ["outputs/TAR1"]


def test_run_violation_keeps_an_unknown_code_as_a_string():
    """Test that a code this SDK version does not know parses instead of raising."""
    violation = DesignRunViolation.model_validate({"code": "brand_new_code", "message": "m"})

    assert violation.code == "brand_new_code"
