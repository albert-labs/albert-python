from pydantic import Field

from albert.resources.base import BaseResource, EntityLink


class Note(BaseResource):
    """Represents a Note on the Albert Platform. Users can be mentioned in notes by using f-string and the User.to_note_mention() method.
    This allows for easy tagging and referencing of users within notes. example: f"Hello {tagged_user.to_note_mention()}!"
    """

    parent_id: str = Field(..., alias="parentId")
    note: str
    id: str | None = Field(default=None, alias="albertId")
    attachments: list[EntityLink] | None = Field(
        default=None, exclude=True, frozen=True, alias="Attachments"
    )
