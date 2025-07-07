from albert import Albert
from albert.resources.btdataset import BTDataset, BTDatasetReferences
from albert.resources.users import User


def test_get_by_id(client: Albert, seeded_btdataset: BTDataset):
    fetched_dataset = client.btdatasets.get_by_id(id=seeded_btdataset.id)
    assert fetched_dataset.id == seeded_btdataset.id


def test_get_all_by_user(client: Albert, static_user: User):
    results = list(client.btdatasets.get_all(created_by=static_user.id, max_items=10))
    assert results, "No datasets returned for the user"
    for dataset in results:
        assert dataset.created.by == static_user.id


def test_get_all_by_name(client: Albert, seeded_btdataset: BTDataset):
    results = list(client.btdatasets.get_all(name=seeded_btdataset.name, max_items=10))
    assert any(ds.id == seeded_btdataset.id for ds in results), "Expected dataset not found"


def test_update(client: Albert, seeded_btdataset: BTDataset):
    seeded_btdataset.key = "test-key"
    seeded_btdataset.file_name = "test-file-name.json"
    seeded_btdataset.references = BTDatasetReferences(
        project_ids=["PRO123"],
        data_column_ids=["DAT123_DAC123"],
    )

    updated_dataset = client.btdatasets.update(dataset=seeded_btdataset)
    assert updated_dataset.key == seeded_btdataset.key
    assert updated_dataset.file_name == seeded_btdataset.file_name
    assert updated_dataset.references == seeded_btdataset.references
