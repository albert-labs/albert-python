from typing import Annotated, TypeVar

from pydantic import PlainSerializer

from albert.core.shared.models.base import BaseResource, EntityLink

EntityType = TypeVar("EntityType", bound=BaseResource)
MetadataItem = float | int | str | EntityLink | list[EntityLink]


def convert_to_entity_link(value: BaseResource | EntityLink) -> EntityLink:
    if isinstance(value, BaseResource):
        return value.to_entity_link()
    return value


"""Type representing a union of `EntityType | EntityLink` that is serialized as a link."""
SerializeAsEntityLink = Annotated[
    EntityType | EntityLink,
    PlainSerializer(convert_to_entity_link),
]
