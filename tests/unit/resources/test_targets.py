import pytest
from pydantic import ValidationError

from albert.resources.targets import (
    ComparisonOperator,
    NumericRange,
    Target,
)


class TestTargetParameterCoercion:
    """Test that TargetParameter.value tolerantly coerces legacy bare scalars."""

    def _validate_target(self, param_value: object) -> Target:
        """Build a minimal Target payload with a parameter carrying the given value."""
        return Target.model_validate(
            {
                "id": "TAR1",
                "name": "test",
                "type": "performance",
                "dataTemplateId": "DAT1",
                "dataColumnId": "DAC1",
                "targetValue": {"operator": "gte", "value": 0},
                "isRequired": True,
                "parameters": [
                    {
                        "id": "PRM1",
                        "category": "Normal",
                        "sequence": "ROW1",
                        "value": param_value,
                    }
                ],
            }
        )

    def test_numeric_scalar_coerces_to_eq(self):
        """Test that a legacy numeric scalar is coerced to operator=eq."""
        target = self._validate_target(25.0)
        pf = target.parameters[0].value
        assert pf.operator == ComparisonOperator.EQ
        assert pf.value == 25.0

    def test_integer_scalar_coerces_to_eq(self):
        """Test that a legacy integer scalar is coerced to operator=eq."""
        target = self._validate_target(80)
        pf = target.parameters[0].value
        assert pf.operator == ComparisonOperator.EQ
        assert pf.value == 80

    def test_string_scalar_coerces_to_in_set(self):
        """Test that a legacy string scalar is coerced to operator=in-set with a single-item list."""
        target = self._validate_target("high")
        pf = target.parameters[0].value
        assert pf.operator == ComparisonOperator.IN_SET
        assert pf.value == ["high"]

    def test_bool_scalar_coerces_to_in_set_not_eq(self):
        """Test that a bool is not mistaken for a numeric and becomes operator=in-set."""
        target = self._validate_target(True)
        pf = target.parameters[0].value
        assert pf.operator == ComparisonOperator.IN_SET

    def test_none_passes_through(self):
        """Test that None is preserved as None (no filter)."""
        target = self._validate_target(None)
        assert target.parameters[0].value is None

    def test_dict_passes_through_as_new_shape(self):
        """Test that an already-structured dict is accepted as the new shape."""
        target = self._validate_target({"operator": "between", "value": {"min": 20, "max": 30}})
        pf = target.parameters[0].value
        assert pf.operator == ComparisonOperator.BETWEEN
        assert isinstance(pf.value, NumericRange)
        assert pf.value.min == 20
        assert pf.value.max == 30

    def test_in_set_list_passes_through(self):
        """Test that a new-shape in-set dict passes through correctly."""
        target = self._validate_target({"operator": "in-set", "value": ["A", "B"]})
        pf = target.parameters[0].value
        assert pf.operator == ComparisonOperator.IN_SET
        assert pf.value == ["A", "B"]

    def test_raw_list_bypasses_coercion_and_fails_criterion_validation(self):
        """Test that a bare list (not the in-set dict shape) is left unchanged and rejected downstream."""
        with pytest.raises(ValidationError):
            self._validate_target([1, 2, 3])
