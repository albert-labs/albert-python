from pydantic import Field

from albert.resources.base import BaseEntityLink, BaseResource


class Note(BaseResource):
    parent_id: str = Field(..., alias="parentId")
    note: str
    id: str | None = Field(default=None, alias="albertId")
    attachments: list[BaseEntityLink] | None = Field(
        default=None, exclude=True, frozen=True, alias="Attachments"
    )
