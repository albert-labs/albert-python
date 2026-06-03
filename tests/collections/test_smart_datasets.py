import pytest

from albert.client import Albert
from albert.core.shared.models.base import Status
from albert.exceptions import NotFoundError
from albert.resources.projects import Project
from albert.resources.smart_datasets import (
    SmartDataset,
    SmartDatasetAggregateBy,
    SmartDatasetBuildState,
    SmartDatasetData,
    SmartDatasetScope,
)
from albert.resources.targets import Target
from tests.seeding import generate_smart_dataset_seed

ignore_in_ten0 = pytest.mark.xfail(
    reason="No DWH available in TEN0 test environment.",
    strict=False,
)


@pytest.fixture(scope="session")
def seeded_smart_dataset_scope(
    seeded_projects: list[Project],
    seeded_targets: list[Target],
) -> SmartDatasetScope:
    return generate_smart_dataset_seed(
        seeded_projects=seeded_projects,
        seeded_targets=seeded_targets,
    )


def test_smart_dataset_create(client: Albert, seeded_smart_dataset_scope: SmartDatasetScope):
    """Test creating a new smart dataset."""

    created = client.smart_datasets.create(scope=seeded_smart_dataset_scope, build=False)
    assert isinstance(created, SmartDataset)
    assert created.id is not None
    assert created.type == "smart"
    assert created.scope.project_ids == seeded_smart_dataset_scope.project_ids
    assert created.scope.target_ids == seeded_smart_dataset_scope.target_ids

    # cleanup
    client.smart_datasets.delete(id=created.id)


@ignore_in_ten0
def test_smart_dataset_create_with_build(
    client: Albert, seeded_smart_dataset_scope: SmartDatasetScope
):
    """Test creating a smart dataset with build=True triggers an async build."""

    created = client.smart_datasets.create(scope=seeded_smart_dataset_scope, build=True)
    assert isinstance(created, SmartDataset)
    assert created.id is not None
    assert created.build_state in (SmartDatasetBuildState.BUILDING, SmartDatasetBuildState.READY)

    # cleanup
    client.smart_datasets.delete(id=created.id)


def test_smart_dataset_get_all(client: Albert):
    """Test listing smart datasets."""
    results = client.smart_datasets.get_all()
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(r, SmartDataset) for r in results)


def test_smart_dataset_get_by_id(client: Albert, seeded_smart_dataset: SmartDataset):
    """Test retrieving a smart dataset by its ID."""
    fetched = client.smart_datasets.get_by_id(id=seeded_smart_dataset.id)
    assert isinstance(fetched, SmartDataset)
    assert fetched.id == seeded_smart_dataset.id


def test_smart_dataset_update(client: Albert, seeded_smart_dataset: SmartDataset):
    """Test updating a smart dataset scope."""
    fetched = client.smart_datasets.get_by_id(id=seeded_smart_dataset.id)

    # update the build state
    fetched.build_state = SmartDatasetBuildState.FAILED

    # update the storage key
    fetched.storage_key = f"smart/datasets/{fetched.id}.json"

    # update the schema
    new_schema = {"experiments": {"variables": ["x", "z"]}}
    fetched.schema_ = new_schema

    updated = client.smart_datasets.update(smart_dataset=fetched)
    assert isinstance(updated, SmartDataset)
    assert updated.id == seeded_smart_dataset.id
    assert updated.build_state == SmartDatasetBuildState.FAILED
    assert updated.storage_key == f"smart/datasets/{fetched.id}.json"
    assert updated.schema_ == new_schema


def test_smart_dataset_delete(
    client: Albert,
    seeded_smart_dataset_scope: SmartDatasetScope,
):
    """Test creating and deleting a smart dataset."""
    created = client.smart_datasets.create(scope=seeded_smart_dataset_scope)
    assert created.id is not None
    assert created.status == Status.ACTIVE

    # delete and verify
    client.smart_datasets.delete(id=created.id)
    with pytest.raises(NotFoundError):
        client.smart_datasets.get_by_id(id=created.id)


@ignore_in_ten0
def test_smart_dataset_get_data(client: Albert, seeded_built_smart_dataset: SmartDataset):
    """Test retrieving the experiment data matrix for a smart dataset."""
    result = client.smart_datasets.get_data(id=seeded_built_smart_dataset.id)
    assert isinstance(result, SmartDatasetData)
    assert result.aggregate_by == SmartDatasetAggregateBy.PTD


@ignore_in_ten0
def test_smart_dataset_get_data_with_filters(
    client: Albert, seeded_built_smart_dataset: SmartDataset
):
    """Test retrieving experiment data with aggregation and identifier/variable filters."""
    result = client.smart_datasets.get_data(
        id=seeded_built_smart_dataset.id,
        aggregate_by=SmartDatasetAggregateBy.WFL,
    )
    assert isinstance(result, SmartDatasetData)
    assert result.aggregate_by == SmartDatasetAggregateBy.WFL

    identifier_keys = [i.key for i in result.identifiers[:1]]
    variable_keys = [v.key for v in result.variables[:1]]
    filtered = client.smart_datasets.get_data(
        id=seeded_built_smart_dataset.id,
        aggregate_by=SmartDatasetAggregateBy.WFL,
        ids=identifier_keys,
        variables=variable_keys,
    )
    assert isinstance(filtered, SmartDatasetData)
    if identifier_keys:
        assert {i.key for i in filtered.identifiers} <= set(identifier_keys)
    if variable_keys:
        assert {v.key for v in filtered.variables} <= set(variable_keys)
