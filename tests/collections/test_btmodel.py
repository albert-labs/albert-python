import uuid

import pytest

from albert import Albert
from albert.resources.btmodel import BTModel, BTModelRegistry, BTModelSession


@pytest.fixture
def model_session(client: Albert) -> BTModelSession:
    # api-btmodel does not have working list/delete functionality,
    # so we need to hard-code an existing resource to play with
    return client.btmodelsessions.get_by_id(id="MDS1")


@pytest.fixture
def model(client: Albert) -> BTModel:
    # api-btmodel does not have working list/delete functionality,
    # so we need to hard-code an existing resource to play with
    return client.btmodels(parent_id="MDS1").get_by_id(id="MDL1")


def test_update_model_session(client: Albert, model_session: BTModelSession):
    marker = f"TEST - {uuid.uuid4()}"
    model_session.registry = BTModelRegistry(build_logs={"status": marker})

    updated_model_session = client.btmodelsessions.update(model_session=model_session)
    assert updated_model_session.registry == model_session.registry


def test_update_model(model_session: BTModelSession, model: BTModel):
    marker = f"TEST - {uuid.uuid4()}"
    model.start_time = marker
    model.end_time = marker
    model.total_time = marker
    model.model_binary_key = marker

    updated_model = model_session.models.update(model=model)
    assert updated_model.start_time == model.start_time
    assert updated_model.end_time == model.end_time
    assert updated_model.total_time == model.total_time
    assert updated_model.model_binary_key == model.model_binary_key
