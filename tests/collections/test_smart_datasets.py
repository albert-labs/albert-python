import pytest

from albert.client import Albert
from albert.core.shared.models.base import Status
from albert.resources.smart_datasets import (
    SmartDataset,
    SmartDatasetScope,
)


@pytest.mark.xfail(reason="Smart Datasets API is not deployed yet.")
def test_smart_dataset_create(client: Albert):
    """Test creating a new smart dataset."""

    # TODO: add a test with build=True once the API is deployed.

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
    """Test updating a smart dataset."""
    smart_dataset = seeded_smart_datasets[0]
    fetched = client.smart_datasets.get_by_id(id=smart_dataset.id)

    # update the storage key
    fetched.storage_key = f"smart/datasets/{smart_dataset.id}.json"
    updated = client.smart_datasets.update(smart_dataset=fetched)
    assert isinstance(updated, SmartDataset)
    assert updated.id == smart_dataset.id
    assert updated.storage_key == f"smart/datasets/{smart_dataset.id}.json"


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
    fetched = client.smart_datasets.get_by_id(id=created.id)
    assert fetched.status == Status.INACTIVE
