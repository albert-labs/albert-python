from pydantic import Field

from albert.core.shared.models.base import BaseResource, EntityLinkWithName


class NoteAttachmentEntityLink(EntityLinkWithName):
    """A file attached to a note, with an optional signed download URL.

    Returned as part of a [`Note`][albert.resources.notes.Note] when it has attached files. Not
    constructed directly; files are attached via the
    [`AttachmentCollection`][albert.collections.attachments.AttachmentCollection].

    Attributes
    ----------
    id : str
        The ID of the linked attachment entity.
    name : str | None
        The display name of the attached file.
    key : str | None
        The storage key of the underlying file.
    file_size : int | None
        The size of the file in bytes.
    signed_url : str | None
        A temporary signed URL for downloading the file, when available.
    """

    key: str | None = None
    file_size: int | None = Field(default=None, alias="fileSize")
    signed_url: str | None = Field(default=None, alias="signedURL")


class Note(BaseResource):
    """A free-text note attached to another entity in Albert.

    A note records a comment or observation against a parent entity (its
    ``parent_id``), such as a Task, Project, or Inventory Item. Users can be
    mentioned inside the ``note`` text by embedding
    [`to_note_mention`][albert.resources.users.User.to_note_mention] in an f-string, for
    example ``f"Hello {tagged_user.to_note_mention()}!"``. Notes are managed
    through the [`NotesCollection`][albert.collections.notes.NotesCollection].

    !!! example
        ```python
        from albert.resources.notes import Note
        note = Note(parent_id="TASA1", note="Reviewed the results.")
        ```

    Attributes
    ----------
    parent_id : str
        The ID of the entity the note is attached to (e.g. a Task ID). Must
        include the full entity prefix.
    note : str
        The text content of the note.
    id : str | None
        The Albert ID of the note. Assigned by Albert when the note is created.
    attachments : list[NoteAttachmentEntityLink] | None
        Files attached to the note. Read-only; populated when the note is
        retrieved.
    """

    parent_id: str = Field(..., alias="parentId")
    note: str
    id: str | None = Field(default=None, alias="albertId")
    attachments: list[NoteAttachmentEntityLink] | None = Field(
        default=None, frozen=True, alias="Attachments"
    )
