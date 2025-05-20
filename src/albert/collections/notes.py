from albert.collections.base import BaseCollection, OrderBy
from albert.resources.notes import Note
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class NotesCollection(BaseCollection):
    """NotesCollection is a collection class for managing Note entities in the Albert platform."""

    _updatable_attributes = {"note", "parent_id"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{NotesCollection._api_version}/notes"

    def create(self, *, note: Note) -> Note:
        """
        Creates a new note.

        Parameters
        ----------
        note : str
            The note content.

        Returns
        -------
        Note
            The created note.
        """
        response = self.session.post(
            self.base_path, json=note.model_dump(by_alias=True, exclude_unset=True, mode="json")
        )
        return Note(**response.json())

    def get_by_id(self, *, id: str) -> Note:
        """
        Retrieves a note by its ID.

        Parameters
        ----------
        id : str
            The ID of the note to retrieve.

        Returns
        -------
        Note
            The note if found, None otherwise.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return Note(**response.json())

    def update(self, *, note: Note) -> Note:
        """Updates a note.

        Parameters
        ----------
        note : Note
            The note to update. The note must have an ID.

        Returns
        -------
        Note
            The updated note as returned by the server.
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
        """
        Deletes a note by its ID.

        Parameters
        ----------
        id : str
            The ID of the note to delete.
        """
        self.session.delete(f"{self.base_path}/{id}")

    def list(self, *, parent_id: str, order_by: OrderBy = OrderBy.DESCENDING) -> list[Note]:
        """
        Lists notes by their parent ID.

        Parameters
        ----------
        parent_id : str
            The parent ID of the notes to list.
        order_by : OrderBy, optional
            The order to list notes in, by default OrderBy.DESCENDING.

        Returns
        -------
        List[Note]
            The list of notes.
        """

        params = {"parentId": parent_id, "orderBy": order_by.value}
        return AlbertPaginator(
            session=self.session,
            path=self.base_path,
            mode=PaginationMode.KEY,
            params=params,
            deserialize=lambda items: [Note(**item) for item in items],
        )
