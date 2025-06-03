from albert.resources.base import BaseResource, EntityLink
from albert.resources.serialization import SerializeAsEntityLink


class FakeEntity(BaseResource):
    id: str
    name: str
    data: float


class FakeResource(BaseResource):
    entity: SerializeAsEntityLink[FakeEntity] | None
    entity_list: list[SerializeAsEntityLink[FakeEntity]]


def test_serialize_as_entity_link():
    entity = FakeEntity(id="E123", name="test-entity", data=4.0)
    link = entity.to_entity_link()
    assert link.id == entity.id

    container = FakeResource(entity=entity, entity_list=[entity, link])
    container = FakeResource(**container.model_dump(mode="json"))

    # FakeEntity values are converted to EntityLink after round-trip serialization
    assert isinstance(container.entity, EntityLink)
    for entity in container.entity_list:
        assert isinstance(entity, EntityLink)

    # Test with optional values
    container = FakeResource(entity=None, entity_list=[])
    container = FakeResource(**container.model_dump(mode="json"))
    assert container.entity is None
    assert not container.entity_list
