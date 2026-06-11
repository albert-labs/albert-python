import pytest

from albert.client import Albert
from albert.core.shared.enums import Status
from albert.exceptions import NotFoundError
from albert.resources.data_templates import DataTemplate
from albert.resources.parameters import Parameter
from albert.resources.targets import (
    ComparisonOperator,
    NumericRange,
    Target,
    TargetParameter,
    TargetType,
    ValueFilter,
)


def test_target_create(
    client: Albert, seed_prefix: str, seeded_data_templates: list[DataTemplate]
):
    """Test creating a new performance target."""

    number_template = [
        x for x in seeded_data_templates if x.name == f"{seed_prefix} - Number Validation Template"
    ].pop()
    number_data_column = number_template.data_column_values[0]

    name = f"{seed_prefix} - Test Target"
    target = Target(
        name=name,
        data_template_id=number_template.id,
        data_column_id=number_data_column.data_column_id,
        type=TargetType.PERFORMANCE,
        target_value=ValueFilter(operator=ComparisonOperator.LTE, value=100),
        is_required=True,
    )
    created = client.targets.create(target=target)
    assert isinstance(created, Target)
    assert created.id.startswith("TAR")
    assert created.name == name
    assert created.data_template_id == number_template.id
    assert created.data_column_id == number_data_column.data_column_id
    assert created.type == TargetType.PERFORMANCE
    assert created.target_value.operator == ComparisonOperator.LTE
    assert created.target_value.value == 100
    assert created.is_required is True

    # cleanup
    client.targets.delete(id=created.id)


def test_target_get_by_id(client: Albert, seeded_targets: list[Target]):
    """Test retrieving a target by its ID."""
    target = seeded_targets[0]
    fetched = client.targets.get_by_id(id=target.id)
    assert isinstance(fetched, Target)
    assert fetched.id == target.id
    assert fetched.name == target.name


def test_target_get_by_ids(client: Albert, seeded_targets: list[Target]):
    """Test bulk fetching targets by IDs."""
    ids = [t.id for t in seeded_targets[:2]]
    results = client.targets.get_by_ids(ids=ids)
    assert isinstance(results, list)
    assert len(results) == 2
    fetched_ids = {t.id for t in results}
    for target_id in ids:
        assert target_id in fetched_ids


def test_target_delete(client: Albert, seed_prefix: str, seeded_targets: list[Target]):
    """Test creating and deleting a target."""

    # create a new target
    target = Target(
        name=f"{seed_prefix} - Test Target",
        data_template_id=seeded_targets[0].data_template_id,
        data_column_id=seeded_targets[0].data_column_id,
        type=TargetType.PERFORMANCE,
        target_value=ValueFilter(operator=ComparisonOperator.EQ, value=42),
        is_required=False,
    )
    created = client.targets.create(target=target)
    assert created.id.startswith("TAR")
    assert created.status == Status.ACTIVE

    # delete the target and verify it is inactive
    client.targets.delete(id=created.id)

    with pytest.raises(NotFoundError):
        client.targets.get_by_id(id=created.id)


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


@pytest.mark.xfail(
    strict=False,
    reason="Requires api-targets backend to accept operator/value-pair TargetParameter.value (ML-1207). Remove decorator once deployed.",
)
def test_target_create_with_between_parameter_filter(
    client: Albert,
    seed_prefix: str,
    seeded_data_templates: list[DataTemplate],
    seeded_parameters: list[Parameter],
):
    """Test creating a target with a between parameter filter and reading it back."""
    params_template = next(
        x for x in seeded_data_templates if x.name == f"{seed_prefix} - Parameters Data Template"
    )
    params_col = params_template.data_column_values[0]

    target = Target(
        name=f"{seed_prefix} - Test Target With Between Param",
        data_template_id=params_template.id,
        data_column_id=params_col.data_column_id,
        type=TargetType.PERFORMANCE,
        target_value=ValueFilter(operator=ComparisonOperator.GTE, value=0),
        is_required=False,
        parameters=[
            TargetParameter(
                id=seeded_parameters[0].id,
                category=seeded_parameters[0].category,
                value=ValueFilter(
                    operator=ComparisonOperator.BETWEEN,
                    value=NumericRange(min=20, max=30),
                ),
                sequence="ROW1",
            )
        ],
    )
    created = client.targets.create(target=target)
    assert isinstance(created, Target)
    assert created.parameters is not None
    assert len(created.parameters) == 1
    pf = created.parameters[0].value
    assert pf is not None
    assert pf.operator == ComparisonOperator.BETWEEN
    assert isinstance(pf.value, NumericRange)
    assert pf.value.min == 20
    assert pf.value.max == 30

    # cleanup
    client.targets.delete(id=created.id)
