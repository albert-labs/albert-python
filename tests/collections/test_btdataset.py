import uuid

import pytest

from albert import Albert
from albert.resources.btdataset import BTDataset


@pytest.fixture
def dataset(client: Albert) -> BTDataset:
    # api-btdataset does not have working list/delete functionality,
    # so we need to hard-code an existing resource to play with
    return client.btdatasets.get_by_id(id="DST1")


def test_update(client: Albert, dataset: BTDataset):
    marker = f"TEST - {uuid.uuid4()}"
    dataset.key = marker
    dataset.file_name = marker

    updated_dataset = client.btdatasets.update(dataset=dataset)
    assert updated_dataset.key == dataset.key
    assert updated_dataset.file_name == dataset.file_name
