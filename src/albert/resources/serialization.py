from typing import Annotated, TypeVar

from pydantic import PlainSerializer

from albert.resources.base import BaseEntityLink, BaseResource


def convert_to_entity_link(value: BaseResource | BaseEntityLink) -> BaseEntityLink:
    if isinstance(value, BaseResource):
        return value.to_entity_link()
    return value


EntityType = TypeVar("EntityType", bound=BaseResource)

SerializeAsEntityLink = Annotated[
    EntityType | BaseEntityLink,
    PlainSerializer(convert_to_entity_link),
]
"""Type representing a union of `EntityType | BaseEntityLink` that is serialized as a link."""
