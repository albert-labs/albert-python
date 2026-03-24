import pytest

from albert.client import Albert
from albert.core.shared.models.base import Status
from albert.exceptions import NotFoundError
from albert.resources.smart_datasets import SmartDataset, SmartDatasetBuildState, SmartDatasetScope

# TODO: update with real project and target IDs once service is deployed to prod


@pytest.mark.xfail(reason="Smart Datasets API is not deployed yet.")
def test_smart_dataset_create(client: Albert):
    """Test creating a new smart dataset."""

    scope = SmartDatasetScope(
        project_ids=["PRO123"],
        target_ids=["TAR123"],
    )
    created = client.smart_datasets.create(scope=scope, build=False)
    assert isinstance(created, SmartDataset)
    assert created.id is not None
    assert created.type == "smart"
    assert created.scope.project_ids == ["PRO123"]
    assert created.scope.target_ids == ["TAR123"]

    # cleanup
    client.smart_datasets.delete(id=created.id)


@pytest.mark.xfail(reason="Smart Datasets API is not deployed yet.")
def test_smart_dataset_create_with_build(client: Albert):
    """Test creating a smart dataset with build=True triggers an async build."""

    scope = SmartDatasetScope(
        project_ids=["PRO123"],
        target_ids=["TAR123"],
    )
    created = client.smart_datasets.create(scope=scope, build=True)
    assert isinstance(created, SmartDataset)
    assert created.id is not None
    assert created.build_state in (SmartDatasetBuildState.BUILDING, SmartDatasetBuildState.READY)

    # cleanup
    client.smart_datasets.delete(id=created.id)


@pytest.mark.xfail(reason="Smart Datasets API is not deployed yet.")
def test_smart_dataset_get_all(client: Albert, seeded_smart_datasets: list[SmartDataset]):
    """Test listing smart datasets."""
    results = client.smart_datasets.get_all()
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(r, SmartDataset) for r in results)


@pytest.mark.xfail(reason="Smart Datasets API is not deployed yet.")
def test_smart_dataset_get_by_id(client: Albert, seeded_smart_datasets: list[SmartDataset]):
    """Test retrieving a smart dataset by its ID."""
    smart_dataset = seeded_smart_datasets[0]
    fetched = client.smart_datasets.get_by_id(id=smart_dataset.id)
    assert isinstance(fetched, SmartDataset)
    assert fetched.id == smart_dataset.id


@pytest.mark.xfail(reason="Smart Datasets API is not deployed yet.")
def test_smart_dataset_update(client: Albert, seeded_smart_datasets: list[SmartDataset]):
    """Test updating a smart dataset scope."""
    smart_dataset = seeded_smart_datasets[0]
    fetched = client.smart_datasets.get_by_id(id=smart_dataset.id)

    # update the scope
    fetched.scope = SmartDatasetScope(
        project_ids=fetched.scope.project_ids,
        target_ids=["TAR456"],
    )
    updated = client.smart_datasets.update(smart_dataset=fetched, build=False)
    assert isinstance(updated, SmartDataset)
    assert updated.id == smart_dataset.id
    assert updated.scope.target_ids == ["TAR456"]


@pytest.mark.xfail(reason="Smart Datasets API is not deployed yet.")
def test_smart_dataset_update_with_build(
    client: Albert, seeded_smart_datasets: list[SmartDataset]
):
    """Test updating a smart dataset scope with build=True."""
    smart_dataset = seeded_smart_datasets[0]
    fetched = client.smart_datasets.get_by_id(id=smart_dataset.id)

    # update the scope
    fetched.scope = SmartDatasetScope(
        project_ids=fetched.scope.project_ids,
        target_ids=["TAR789"],
    )
    updated = client.smart_datasets.update(smart_dataset=fetched, build=True)
    assert isinstance(updated, SmartDataset)
    assert updated.id == smart_dataset.id


@pytest.mark.xfail(reason="Smart Datasets API is not deployed yet.")
def test_smart_dataset_update_build_state(
    client: Albert, seeded_smart_datasets: list[SmartDataset]
):
    """Test updating the build state of a smart dataset."""
    smart_dataset = seeded_smart_datasets[0]
    fetched = client.smart_datasets.get_by_id(id=smart_dataset.id)

    fetched.build_state = SmartDatasetBuildState.READY
    updated = client.smart_datasets.update(smart_dataset=fetched, build=False)
    assert isinstance(updated, SmartDataset)
    assert updated.id == smart_dataset.id
    assert updated.build_state == SmartDatasetBuildState.READY


@pytest.mark.xfail(reason="Smart Datasets API is not deployed yet.")
def test_smart_dataset_update_storage_key(
    client: Albert, seeded_smart_datasets: list[SmartDataset]
):
    """Test updating the storage key of a smart dataset."""
    smart_dataset = seeded_smart_datasets[0]
    fetched = client.smart_datasets.get_by_id(id=smart_dataset.id)

    fetched.storage_key = f"smart/datasets/{smart_dataset.id}.json"
    updated = client.smart_datasets.update(smart_dataset=fetched, build=False)
    assert isinstance(updated, SmartDataset)
    assert updated.id == smart_dataset.id
    assert updated.storage_key == f"smart/datasets/{smart_dataset.id}.json"


@pytest.mark.xfail(reason="Smart Datasets API is not deployed yet.")
def test_smart_dataset_update_schema(client: Albert, seeded_smart_datasets: list[SmartDataset]):
    """Test updating the schema of a smart dataset."""
    smart_dataset = seeded_smart_datasets[0]
    fetched = client.smart_datasets.get_by_id(id=smart_dataset.id)

    new_schema = {"experiments": {"variables": ["x", "y"]}}
    fetched.schema_ = new_schema
    updated = client.smart_datasets.update(smart_dataset=fetched, build=False)
    assert isinstance(updated, SmartDataset)
    assert updated.id == smart_dataset.id
    assert updated.schema_ == new_schema


@pytest.mark.xfail(reason="Smart Datasets API is not deployed yet.")
def test_smart_dataset_delete(client: Albert):
    """Test creating and deleting a smart dataset."""
    scope = SmartDatasetScope(
        project_ids=["PRO123"],
        target_ids=["TAR123"],
    )
    created = client.smart_datasets.create(scope=scope, build=False)
    assert created.id is not None
    assert created.status == Status.ACTIVE

    # delete and verify
    client.smart_datasets.delete(id=created.id)
    with pytest.raises(NotFoundError):
        client.smart_datasets.get_by_id(id=created.id)
