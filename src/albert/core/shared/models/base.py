from datetime import datetime

from pydantic import Field, PrivateAttr

from albert.core.base import BaseAlbertModel
from albert.core.session import AlbertSession
from albert.core.shared.enums import Status
from albert.exceptions import AlbertException


class AuditFields(BaseAlbertModel):
    """The audit fields for a resource"""

    by: str = Field(default=None)
    by_name: str | None = Field(default=None, alias="byName")
    at: datetime | None = Field(default=None)


class EntityLink(BaseAlbertModel):
    id: str
    name: str | None = Field(default=None, exclude=True)

    def to_entity_link(self) -> "EntityLink":
        # Convience method to return self, so you can call this method on objects that are already entity links
        return self


class EntityLinkWithName(EntityLink):
    """EntityLink that includes the name field in serialization."""

    name: str | None = Field(default=None, exclude=False)


class LocalizedNames(BaseAlbertModel):
    de: str | None = None
    ja: str | None = None
    zh: str | None = None
    es: str | None = None


class BaseResource(BaseAlbertModel):
    """The base resource for all Albert resources.

    Attributes
    ----------
    status: Status | None
        The status of the resource, optional.
    created: AuditFields | None
        Audit fields for the creation of the resource, optional.
    updated: AuditFields | None
        Audit fields for the update of the resource, optional.
    """

    status: Status | None = Field(default=None)

    # Read-only fields
    created: AuditFields | None = Field(
        default=None,
        alias="Created",
        exclude=True,
        frozen=True,
    )
    updated: AuditFields | None = Field(
        default=None,
        alias="Updated",
        exclude=True,
        frozen=True,
    )

    def to_entity_link(self) -> EntityLink:
        if id := getattr(self, "id", None):
            return EntityLink(id=id)
        raise AlbertException(
            "A non-null 'id' is required to create an entity link. "
            "Ensure the linked object is registered and has a valid 'id'."
        )


class BaseSessionResource(BaseResource):
    _session: AlbertSession | None = PrivateAttr(default=None)

    def __init__(self, **data):
        super().__init__(**data)
        self._session = data.get("session")

    @property
    def session(self) -> AlbertSession | None:
        return self._session
