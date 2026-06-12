from pydantic import Field

from albert.core.shared.models.base import BaseResource, EntityLinkWithName


class NoteAttachmentEntityLink(EntityLinkWithName):
    """An entity link to a file attachment on a note, including download metadata.

    Attributes
    ----------
    id : str
        The Albert ID of the attachment.
    name : str | None
        The display name of the attachment.
    key : str | None
        The storage key of the attached file.
    file_size : int | None
        The size of the file in bytes.
    signed_url : str | None
        A pre-signed download URL for the attachment.
    """

    key: str | None = None
    file_size: int | None = Field(default=None, alias="fileSize")
    signed_url: str | None = Field(default=None, alias="signedURL")


class Note(BaseResource):
    """A note attached to an entity such as a Task, Project, or Inventory item.

    Users can be @-mentioned by embedding ``User.to_note_mention()`` in the note text,
    for example: ``f"Hello {user.to_note_mention()}!"``.

    Attributes
    ----------
    parent_id : str
        The Albert ID of the entity this note belongs to.
    note : str
        The note content. May contain @-mention markers.
    id : str | None
        The Albert ID of the note.
    attachments : list[NoteAttachmentEntityLink] | None
        Files attached to this note. Read-only.
    """

    parent_id: str = Field(..., alias="parentId")
    note: str
    id: str | None = Field(default=None, alias="albertId")
    attachments: list[NoteAttachmentEntityLink] | None = Field(
        default=None, frozen=True, alias="Attachments"
    )
