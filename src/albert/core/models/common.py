from datetime import datetime

from pydantic import Field

from albert.core.base import BaseAlbertModel


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


class LocalizedNames(BaseAlbertModel):
    de: str | None = None
    ja: str | None = None
    zh: str | None = None
    es: str | None = None
