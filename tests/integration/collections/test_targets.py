import pytest

from albert.client import Albert
from albert.core.shared.enums import Status
from albert.exceptions import NotFoundError
from albert.resources.data_templates import DataTemplate
from albert.resources.parameters import Parameter
from albert.resources.targets import (
    ComparisonOperator,
    Criterion,
    NumericRange,
    Target,
    TargetParameter,
    TargetType,
)

pytestmark = pytest.mark.xdist_group("datatemplates")


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
        target_value=Criterion(operator=ComparisonOperator.LTE, value=100),
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
        target_value=Criterion(operator=ComparisonOperator.EQ, value=42),
        is_required=False,
    )
    created = client.targets.create(target=target)
    assert created.id.startswith("TAR")
    assert created.status == Status.ACTIVE

    # delete the target and verify it is inactive
    client.targets.delete(id=created.id)

    with pytest.raises(NotFoundError):
        client.targets.get_by_id(id=created.id)


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
        target_value=Criterion(operator=ComparisonOperator.GTE, value=0),
        is_required=False,
        parameters=[
            TargetParameter(
                id=seeded_parameters[0].id,
                category=seeded_parameters[0].category,
                value=Criterion(
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
