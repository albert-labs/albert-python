import uuid

import pytest

from albert.client import Albert
from albert.exceptions import AlbertHTTPError
from albert.resources.targets import Target, TargetOperator, TargetType, TargetValue


def test_target_create(client: Albert):
    """Test creating a new performance target."""
    name = f"TEST_TAR_{uuid.uuid4()}"
    target = Target(
        name=name,
        data_template_id="DAT123",
        data_column_id="DAC123",
        type=TargetType.PERFORMANCE,
        target_value=TargetValue(operator=TargetOperator.LTE, value=100),
        is_required=True,
    )
    created = client.targets.create(target=target)
    assert isinstance(created, Target)
    assert created.id.startswith("TAR")
    assert created.name == name
    assert created.data_template_id == "DAT123"
    assert created.data_column_id == "DAC123"
    assert created.type == TargetType.PERFORMANCE
    assert created.target_value.operator == TargetOperator.LTE
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


def test_target_list(client: Albert, seeded_targets: list[Target]):
    """Test listing targets."""
    results = client.targets.list()
    assert isinstance(results, list)
    assert len(results) > 0
    for target in results:
        assert isinstance(target, Target)


# def test_target_list_by_project_id(client: Albert, seeded_targets: list[Target]):
#     """Test listing targets by project ID."""
#     # TODO: implement this once the API supports it
#     results = client.targets.list(project_id="...")
#     assert isinstance(results, list)
#     assert len(results) > 0
#     for target in results:
#         assert isinstance(target, Target)


def test_target_delete(client: Albert, seeded_targets: list[Target]):
    """Test creating and deleting a target."""

    # create a new target
    target = Target(
        name=f"TEST_TAR_{uuid.uuid4()}",
        data_template_id=seeded_targets[0].data_template_id,
        data_column_id=seeded_targets[0].data_column_id,
        type=TargetType.PERFORMANCE,
        target_value=TargetValue(operator=TargetOperator.EQ, value=42),
        is_required=False,
    )
    created = client.targets.create(target=target)
    assert created.id.startswith("TAR")

    # delete the target and verify it is deleted
    client.targets.delete(id=created.id)
    with pytest.raises(AlbertHTTPError):
        client.targets.get_by_id(id=created.id)
