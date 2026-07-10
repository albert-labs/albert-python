from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy
from albert.resources.notes import Note


class NotesCollection(BaseCollection):
    """Manage Notes in the Albert platform.

    A Note is a free-text comment attached to another entity (its "parent"),
    such as a Task, Project, or Inventory Item. Notes are commonly used to record
    observations, discussion, or context alongside an entity. Users can be
    mentioned inside a note's text via :meth:`~albert.resources.users.User.to_note_mention`,
    and files can be attached to a note through the
    :class:`~albert.collections.attachments.AttachmentCollection`.

    This collection is accessed as ``client.notes``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for note requests.

    Methods
    -------
    create(note) -> Note
        Create a new note attached to a parent entity.
    get_by_id(id) -> Note
        Retrieve a single note by its ID.
    update(note) -> Note
        Apply changes to an existing note.
    delete(id) -> None
        Delete a note by its ID.
    get_by_parent_id(parent_id, order_by=OrderBy.DESCENDING) -> list[Note]
        List all notes attached to a given parent entity.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert
        client = Albert()
        note = client.notes.create(
            note=Note(parent_id="TASA1", note="Reviewed the results.")
        )
        print(note.id)
        ```
    """

    _updatable_attributes = {"note", "parent_id"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{NotesCollection._api_version}/notes"

    def create(self, *, note: Note) -> Note:
        """Create a new note.

        Parameters
        ----------
        note : Note
            The note to create. Requires ``parent_id`` (the entity the note is
            attached to) and ``note`` (the text content).

        Returns
        -------
        Note
            The created note, populated with its assigned ID.

        Examples
        --------
        !!! example
            ```python
            from albert.resources.notes import Note
            note = client.notes.create(
                note=Note(parent_id="TASA1", note="Kicked off the experiment.")
            )
            print(note.id)
            ```
        """
        response = self.session.post(
            self.base_path, json=note.model_dump(by_alias=True, exclude_unset=True, mode="json")
        )
        return Note(**response.json())

    def get_by_id(self, *, id: str) -> Note:
        """Retrieve a note by its ID.

        Parameters
        ----------
        id : str
            The ID of the note to retrieve.

        Returns
        -------
        Note
            The matching note.

        Examples
        --------
        !!! example
            ```python
            note = client.notes.get_by_id(id="...")
            note.note
            # 'Reviewed the results.'
            ```
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return Note(**response.json())

    def update(self, *, note: Note) -> Note:
        """Update a note.

        Fetches the current note, diffs it against the supplied one, and applies
        the changes.

        Parameters
        ----------
        note : Note
            The note with updated fields. Must include ``id``.

        Returns
        -------
        Note
            The updated note as returned by the server.

        Notes
        -----
        The following fields can be updated: ``note``, ``parent_id``.

        Examples
        --------
        !!! example
            ```python
            note = client.notes.get_by_id(id="...")
            note.note = "Updated comment."
            updated = client.notes.update(note=note)
            ```
        """
        patch = self._generate_patch_payload(
            existing=self.get_by_id(id=note.id), updated=note, generate_metadata_diff=False
        )
        self.session.patch(
            f"{self.base_path}/{note.id}",
            json=patch.model_dump(mode="json", by_alias=True, exclude_unset=True),
        )
        return self.get_by_id(id=note.id)

    def delete(self, *, id: str) -> None:
        """Delete a note by its ID.

        Parameters
        ----------
        id : str
            The ID of the note to delete.

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            client.notes.delete(id="...")
            ```
        """
        self.session.delete(f"{self.base_path}/{id}")

    def get_by_parent_id(
        self,
        *,
        parent_id: str,
        order_by: OrderBy = OrderBy.DESCENDING,
    ) -> list[Note]:
        """List all notes attached to a parent entity.

        Parameters
        ----------
        parent_id : str
            The ID of the parent entity whose notes should be listed (e.g. a Task
            ID such as ``"TASA1"``). Must include the full entity prefix.
        order_by : OrderBy, optional
            The order to return notes in. Defaults to ``OrderBy.DESCENDING``.

        Returns
        -------
        list[Note]
            The notes attached to the parent entity.

        Examples
        --------
        !!! example
            ```python
            notes = client.notes.get_by_parent_id(parent_id="TASA1")
            for note in notes:
                print(note.note)
            ```
        """
        params = {
            "parentId": parent_id,
            "orderBy": order_by,
        }
        response = self.session.get(
            url=self.base_path,
            params=params,
        )
        return [Note(**x) for x in response.json()["Items"]]
