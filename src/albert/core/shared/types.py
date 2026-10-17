from typing import Annotated, TypeVar

from pydantic import GetCoreSchemaHandler, PlainSerializer
from pydantic_core import core_schema

from albert.core.shared.models.base import BaseResource, EntityLink, EntityLinkWithName

EntityType = TypeVar("EntityType", bound=BaseResource)
# ``None`` covers custom fields the platform returns as null after a user clears them.
MetadataItem = (
    float
    | int
    | str
    | EntityLinkWithName
    | EntityLink
    | list[EntityLinkWithName | EntityLink]
    | None
)


class _UnsetType:
    """Sentinel type for distinguishing unset parameters from explicit ``None``."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: object, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.is_instance_schema(cls)


_UNSET = _UnsetType()


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
