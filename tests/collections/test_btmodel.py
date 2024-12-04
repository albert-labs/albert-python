from albert import Albert
from albert.resources.btmodel import BTModel, BTModelRegistry, BTModelSession


def test_update_model_session(client: Albert, static_btmodelsession: BTModelSession):
    model_session = static_btmodelsession.model_copy()

    marker = "TEST"
    model_session.registry = BTModelRegistry(build_logs={"status": marker})

    updated_model_session = client.btmodelsessions.update(model_session=model_session)
    assert updated_model_session.registry == model_session.registry


def test_update_model(static_btmodelsession: BTModelSession, static_btmodel: BTModel):
    model = static_btmodel.model_copy()

    marker = "TEST"
    model.start_time = marker
    model.end_time = marker
    model.total_time = marker
    model.model_binary_key = marker

    updated_model = static_btmodelsession.models.update(model=model)
    assert updated_model.start_time == model.start_time
    assert updated_model.end_time == model.end_time
    assert updated_model.total_time == model.total_time
    assert updated_model.model_binary_key == model.model_binary_key
