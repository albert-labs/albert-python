from albert import Albert
from albert.resources.btmodel import BTModel, BTModelRegistry, BTModelSession


def test_get_model_session_by_id(client: Albert, seeded_btmodelsession: BTModelSession):
    fetched_model_session = client.btmodelsessions.get_by_id(id=seeded_btmodelsession.id)
    assert fetched_model_session.id == seeded_btmodelsession.id


def test_update_model_session(client: Albert, seeded_btmodelsession: BTModelSession):
    marker = "TEST"
    seeded_btmodelsession.registry = BTModelRegistry(build_logs={"status": marker})

    updated_model_session = client.btmodelsessions.update(model_session=seeded_btmodelsession)
    assert updated_model_session.registry == seeded_btmodelsession.registry


def test_get_model_by_id(
    client: Albert,
    seeded_btmodelsession: BTModelSession,
    seeded_btmodel: BTModel,
):
    fetched_model = client.btmodels.get_by_id(
        id=seeded_btmodel.id,
        parent_id=seeded_btmodelsession.id,
    )
    assert fetched_model.id == seeded_btmodel.id


def test_update_model(
    client: Albert,
    seeded_btmodelsession: BTModelSession,
    seeded_btmodel: BTModel,
):
    marker = "TEST"
    seeded_btmodel.start_time = marker
    seeded_btmodel.end_time = marker
    seeded_btmodel.total_time = marker
    seeded_btmodel.model_binary_key = marker

    updated_model = client.btmodels.update(
        model=seeded_btmodel,
        parent_id=seeded_btmodelsession.id,
    )
    assert updated_model.start_time == seeded_btmodel.start_time
    assert updated_model.end_time == seeded_btmodel.end_time
    assert updated_model.total_time == seeded_btmodel.total_time
    assert updated_model.model_binary_key == seeded_btmodel.model_binary_key
