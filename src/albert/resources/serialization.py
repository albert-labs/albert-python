from typing import Annotated, TypeVar

from pydantic import PlainSerializer

from albert.resources.base import BaseResource, EntityLink


def convert_to_entity_link(value: BaseResource | EntityLink) -> EntityLink:
    if isinstance(value, BaseResource):
        return value.to_entity_link()
    return value


EntityType = TypeVar("EntityType", bound=BaseResource)

SerializeAsEntityLink = Annotated[
    EntityType | EntityLink,
    PlainSerializer(convert_to_entity_link),
]
"""Type representing a union of `EntityType | EntityLink` that is serialized as a link."""
