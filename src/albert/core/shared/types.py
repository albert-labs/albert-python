from typing import Annotated, TypeVar

from pydantic import PlainSerializer

from albert.core.shared.models.base import BaseResource, EntityLink, EntityLinkWithName

EntityType = TypeVar("EntityType", bound=BaseResource)
MetadataItem = float | int | str | EntityLink | list[EntityLink]


def convert_to_entity_link(value: BaseResource | EntityLink) -> EntityLink:
    if isinstance(value, BaseResource):
        return value.to_entity_link()
    return value


def convert_to_entity_link_with_name(value: BaseResource | EntityLink) -> EntityLinkWithName:
    """Convert to EntityLinkWithName to ensure name field is included in serialization."""
    if isinstance(value, BaseResource):
        # Create EntityLinkWithName with name included
        return EntityLinkWithName(id=value.id, name=getattr(value, "name", None))
    # If it's already an EntityLink, convert to EntityLinkWithName
    if isinstance(value, EntityLink):
        return EntityLinkWithName(id=value.id, name=value.name)
    return value


"""Type representing a union of `EntityType | EntityLink` that is serialized as a link."""
SerializeAsEntityLink = Annotated[
    EntityType | EntityLink,
    PlainSerializer(convert_to_entity_link),
]


"""Type representing a union of `EntityType | EntityLink` that is serialized as a link with name included."""
SerializeAsEntityLinkWithName = Annotated[
    EntityType | EntityLinkWithName,
    PlainSerializer(convert_to_entity_link_with_name),
]
