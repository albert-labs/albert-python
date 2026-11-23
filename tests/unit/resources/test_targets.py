import pytest
from pydantic import ValidationError

from albert.resources.targets import (
    ComparisonOperator,
    Criterion,
    NumericRange,
    Target,
    TargetType,
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


class TestTargetLabelId:
    """Test that Target round-trips managed and legacy free-text labels."""

    def test_label_id_is_serialized_on_create_payload(self):
        """Test that label_id is included as labelId when dumping a create payload."""
        target = Target(
            name="Viscosity spec",
            type=TargetType.PERFORMANCE,
            data_template_id="DAT1",
            data_column_id="DAC1",
            target_value=Criterion(operator=ComparisonOperator.GTE, value=90),
            is_required=True,
            label_id="LBL1",
        )

        payload = target.model_dump(by_alias=True, exclude_none=True, mode="json")

        assert payload["labelId"] == "LBL1"
        assert "label" not in payload

    def test_label_id_is_normalized_from_bare_numeric(self):
        """Test that a bare numeric label id is prefixed to LBL… on validation."""
        target = Target.model_validate(
            {
                "name": "Viscosity spec",
                "type": "performance",
                "dataTemplateId": "DAT1",
                "dataColumnId": "DAC1",
                "targetValue": {"operator": "gte", "value": 90},
                "isRequired": True,
                "labelId": "1",
            }
        )

        assert target.label_id == "LBL1"

    def test_legacy_label_string_is_accepted(self):
        """Test that the deprecated free-text label field is still accepted on read."""
        target = Target.model_validate(
            {
                "name": "Viscosity spec",
                "type": "performance",
                "dataTemplateId": "DAT1",
                "dataColumnId": "DAC1",
                "targetValue": {"operator": "gte", "value": 90},
                "isRequired": True,
                "label": "Needs",
            }
        )

        assert target.label == "Needs"
        assert target.label_id is None
