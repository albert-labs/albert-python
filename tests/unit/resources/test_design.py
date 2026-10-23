import pytest
from pydantic import ValidationError

from albert.resources.design import DesignObjective
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
