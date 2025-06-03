import mimetypes
from typing import IO

from albert.collections.base import BaseCollection
from albert.collections.files import FileCollection
from albert.collections.notes import NotesCollection
from albert.resources.attachments import Attachment
from albert.resources.files import FileCategory, FileNamespace
from albert.resources.notes import Note


class AttachmentCollection(BaseCollection):
    """AttachmentCollection is a collection class for managing Attachment entities in the Albert platform."""

    _api_version: str = "v3"

    def __init__(self, *, session):
        super().__init__(session=session)
        self.base_path = f"/api/{AttachmentCollection._api_version}/attachments"

    def _get_file_collection(self):
        return FileCollection(session=self.session)

    def _get_note_collection(self):
        return NotesCollection(session=self.session)

    def attach_file_to_note(
        self,
        *,
        note_id: str,
        file_name: str,
        file_key: str,
        category: FileCategory = FileCategory.OTHER,
    ) -> Attachment:
        """Attaches an already uploaded file to a note.

        Parameters
        ----------
        note_id : str
            The ID of the note to attach the file to.
        file_name : str
            The name of the file to attach.
        file_key : str
            The unique key of the file to attach (the returned upload name).
        category : FileCategory, optional
            The type of file, by default FileCategory.OTHER

        Returns
        -------
        Attachment
            The related attachment object.
        """
        attachment = Attachment(
            parent_id=note_id, name=file_name, key=file_key, namespace="result", category=category
        )
        response = self.session.post(
            url=self.base_path,
            json=attachment.model_dump(by_alias=True, mode="json", exclude_unset=True),
        )
        return Attachment(**response.json())

    def delete(self, *, id: str) -> None:
        """Deletes an attachment by ID.

        Parameters
        ----------
        id : str
            The ID of the attachment to delete.
        """
        self.session.delete(f"{self.base_path}/{id}")

    def upload_and_attach_file_as_note(
        self, parent_id: str, file_data: IO, note_text: str = "", file_name: str = ""
    ) -> Note:
        """Uploads a file and attaches it to a new note. A user can be tagged in the note_text string by using f-string and the User.to_note_mention() method.
        This allows for easy tagging and referencing of users within notes. example: f"Hello {tagged_user.to_note_mention()}!"

        Parameters
        ----------
        parent_id : str
            The ID of the parent entity onto which the note will be attached.
        file_data : IO
            The file data to upload.
        note_text : str, optional
            Any additional text to add to the note, by default ""
        file_name : str, optional
            The name of the file, by default ""

        Returns
        -------
        Note
            The created note.
        """
        file_type = mimetypes.guess_type(file_name)[0]
        file_collection = self._get_file_collection()
        note_collection = self._get_note_collection()

        file_collection.sign_and_upload_file(
            data=file_data,
            name=file_name,
            namespace=FileNamespace.RESULT.value,
            content_type=file_type,
        )
        file_info = file_collection.get_by_name(
            name=file_name, namespace=FileNamespace.RESULT.value
        )
        note = Note(
            parent_id=parent_id,
            note=note_text,
        )
        registered_note = note_collection.create(note=note)
        self.attach_file_to_note(
            note_id=registered_note.id,
            file_name=file_name,
            file_key=file_info.name,
        )
        return note_collection.get_by_id(id=registered_note.id)
