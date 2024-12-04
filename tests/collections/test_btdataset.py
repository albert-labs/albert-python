from albert import Albert
from albert.resources.btdataset import BTDataset


def test_update(client: Albert, static_btdataset: BTDataset):
    dataset = static_btdataset.model_copy()

    marker = "TEST"
    dataset.key = marker
    dataset.file_name = marker

    updated_dataset = client.btdatasets.update(dataset=dataset)
    assert updated_dataset.key == dataset.key
    assert updated_dataset.file_name == dataset.file_name
