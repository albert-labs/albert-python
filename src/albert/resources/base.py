from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, PrivateAttr

from albert.session import AlbertSession
from albert.utils.exceptions import AlbertException
from albert.utils.types import BaseAlbertModel


class Status(str, Enum):
    """The status of a resource"""

    ACTIVE = "active"
    INACTIVE = "inactive"


class SecurityClass(str, Enum):
    """The security class of a resource"""

    SHARED = "shared"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"
    PRIVATE = "private"
    PUBLIC = "public"


class AuditFields(BaseAlbertModel):
    """The audit fields for a resource"""

    by: str = Field(None)
    by_name: str | None = Field(None, alias="byName")
    at: datetime | None = Field(None)


class BaseResource(BaseAlbertModel):
    """The base resource for all Albert resources.

    Attributes
    ----------
    created: AuditFields | None
        Audit fields for the creation of the resource, optional.
    updated: AuditFields | None
        Audit fields for the update of the resource, optional.
    status: Status | None
        The status of the resource, optional.
    """

    _created: AuditFields | None = PrivateAttr(default=None)
    _updated: AuditFields | None = PrivateAttr(default=None)
    status: Status | None = Field(default=None)

    def __init__(self, **data: Any):
        super().__init__(**data)
        if "Created" in data:
            self._created = AuditFields(**data["Created"])
        if "Updated" in data:
            self._updated = AuditFields(**data["Updated"])

    @property
    def created(self) -> AuditFields | None:
        return self._created

    @property
    def updated(self) -> AuditFields | None:
        return self._updated


class BaseSessionResource(BaseResource):
    session: AlbertSession | None = Field(
        default=None,
        exclude=True,
        description=(
            "Albert session for accessing the Albert API. "
            "The session is included as an optional field to allow for resources of this type "
            "to be created independently from calls to the API."
        ),
    )


class BaseEntityLink(BaseAlbertModel):
    id: str
    name: str | None = Field(default=None, exclude=True)


class EntityLinkConvertible:
    def to_entity_link(self) -> BaseEntityLink:
        if hasattr(self, "id"):
            return BaseEntityLink(id=self.id)
        return AlbertException(
            "`id` is required to create an entity link. Ensure the linked object is registered."
        )
