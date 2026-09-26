import pytest
from pydantic import ValidationError

from albert.core.shared.models.base import BaseResource, EntityLink, EntityLinkWithName
from albert.core.shared.types import (
    MetadataItem,
    SerializeAsEntityLink,
    SerializeAsEntityLinkWithName,
    convert_to_entity_link,
    convert_to_entity_link_with_name,
)


class FakeEntity(BaseResource):
    id: str
    name: str
    data: float


class FakeResource(BaseResource):
    entity: SerializeAsEntityLink[FakeEntity] | None
    entity_list: list[SerializeAsEntityLink[FakeEntity]]


class FakeNamedResource(BaseResource):
    entity: SerializeAsEntityLinkWithName[FakeEntity] | None
    entity_list: list[SerializeAsEntityLinkWithName[FakeEntity]]


class FakeMetadataHolder(BaseResource):
    metadata: dict[str, MetadataItem]


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


def test_convert_to_entity_link_passes_through_entity_link():
    """Test that convert_to_entity_link returns a plain EntityLink unchanged."""
    link = EntityLink(id="LNK1", name="ignored")

    assert convert_to_entity_link(link) is link


def test_convert_to_entity_link_from_base_resource():
    """Test that convert_to_entity_link builds a link from a BaseResource."""
    entity = FakeEntity(id="E123", name="test-entity", data=4.0)

    link = convert_to_entity_link(entity)
    assert isinstance(link, EntityLink)
    assert link.id == "E123"


def test_convert_to_entity_link_with_name_from_base_resource():
    """Test that convert_to_entity_link_with_name preserves the name field."""
    entity = FakeEntity(id="E123", name="test-entity", data=4.0)

    link = convert_to_entity_link_with_name(entity)
    assert isinstance(link, EntityLinkWithName)
    assert link.model_dump(mode="json") == {"id": "E123", "name": "test-entity"}


def test_convert_to_entity_link_with_name_from_entity_link():
    """Test that convert_to_entity_link_with_name upgrades a plain EntityLink."""
    link = EntityLink(id="LNK1", name="carried-over")

    upgraded = convert_to_entity_link_with_name(link)
    assert isinstance(upgraded, EntityLinkWithName)
    assert upgraded.model_dump(mode="json") == {"id": "LNK1", "name": "carried-over"}


def test_convert_to_entity_link_with_name_from_entity_link_with_name_is_unchanged():
    """Test that convert_to_entity_link_with_name leaves an EntityLinkWithName value unchanged."""
    link = EntityLinkWithName(id="LNK1", name="already-named")

    converted = convert_to_entity_link_with_name(link)
    assert isinstance(converted, EntityLinkWithName)
    assert converted.model_dump(mode="json") == {"id": "LNK1", "name": "already-named"}
    assert converted.model_dump(mode="json") == link.model_dump(mode="json")


def test_convert_to_entity_link_with_name_passes_through_other_values():
    """Test that convert_to_entity_link_with_name returns non-entity values unchanged."""
    assert convert_to_entity_link_with_name("not-an-entity") == "not-an-entity"


def test_serialize_as_entity_link_with_name_round_trip():
    """Test that SerializeAsEntityLinkWithName keeps the name through a dump/validate round trip."""
    entity = FakeEntity(id="E123", name="test-entity", data=4.0)

    container = FakeNamedResource(entity=entity, entity_list=[entity])
    dumped = container.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert dumped["entity"] == {"id": "E123", "name": "test-entity"}
    assert dumped["entity_list"] == [{"id": "E123", "name": "test-entity"}]

    round_tripped = FakeNamedResource(**container.model_dump(mode="json"))
    assert isinstance(round_tripped.entity, EntityLinkWithName)
    assert round_tripped.entity.name == "test-entity"


@pytest.mark.parametrize(
    "value",
    [
        4,
        4.5,
        "plain-string",
        EntityLink(id="LNK1"),
        EntityLinkWithName(id="LNK1", name="named"),
        [EntityLink(id="LNK1"), EntityLinkWithName(id="LNK2", name="named")],
    ],
)
def test_metadata_item_accepts_each_member_of_the_union(value):
    """Test that MetadataItem accepts scalars, entity links, and lists of entity links."""
    holder = FakeMetadataHolder(metadata={"key": value})

    assert holder.metadata["key"] == value


def test_metadata_item_rejects_a_link_without_an_id():
    """Test that MetadataItem rejects a dict lacking the required EntityLink id field."""
    with pytest.raises(ValidationError):
        FakeMetadataHolder(metadata={"key": {"name": "no-id"}})
