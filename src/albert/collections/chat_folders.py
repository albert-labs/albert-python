from __future__ import annotations

from collections.abc import AsyncIterator

from pydantic import validate_call

from albert.core.async_session import AsyncAlbertSession
from albert.core.pagination import AsyncAlbertPaginator
from albert.resources.chats import ChatFolder


class ChatFolderCollection:
    """
    Async collection for managing chat folders (🧪Beta).

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    Parameters
    ----------
    session : AsyncAlbertSession
        The Albert async session instance.

    Attributes
    ----------
    base_path : str
        The base URL for chat folder API requests.

    Methods
    -------
    create(folder) -> ChatFolder
        Creates a new chat folder.
    get_by_id(id) -> ChatFolder
        Retrieves a chat folder by its ID.
    get_all(name, exact_match, max_items) -> AsyncIterator[ChatFolder]
        Iterates over chat folders with optional filters.
    update(id, ...) -> ChatFolder
        Updates a chat folder by ID.
    delete(id) -> None
        Deletes a chat folder by its ID.
    """

    _api_version = "v3"

    def __init__(self, *, session: AsyncAlbertSession):
        """
        Initializes the ChatFolderCollection with the provided session.

        Parameters
        ----------
        session : AsyncAlbertSession
            The async session used to make API requests.
        """
        self._session = session
        self.base_path: str = f"/api/{self._api_version}/chats/folders"

    @validate_call
    async def create(self, *, folder: ChatFolder) -> ChatFolder:
        """
        Create a new chat folder.

        Parameters
        ----------
        folder : ChatFolder
            The folder to create.

        Returns
        -------
        ChatFolder
            The created folder.
        """
        response = await self._session.post(
            self.base_path,
            json=folder.model_dump(by_alias=True, exclude_unset=True, mode="json"),
        )
        return ChatFolder(**response.json())

    @validate_call
    async def get_by_id(self, *, id: str) -> ChatFolder:
        """
        Retrieve a chat folder by its ID.

        Parameters
        ----------
        id : str
            The folder ID.

        Returns
        -------
        ChatFolder
            The matching folder.
        """
        response = await self._session.get(f"{self.base_path}/{id}")
        return ChatFolder(**response.json())

    @validate_call
    async def get_all(
        self,
        *,
        name: list[str] | None = None,
        exact_match: bool = False,
        max_items: int | None = None,
    ) -> AsyncIterator[ChatFolder]:
        """
        Iterate over chat folders with optional filters.

        Parameters
        ----------
        name : list[str] | None, optional
            Filter by folder name(s).
        exact_match : bool, optional
            Whether name filtering uses exact matching (default False).
        max_items : int | None, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Yields
        ------
        ChatFolder
            Folders matching the given filters.
        """
        params: dict[str, str | list[str]] = {}
        if name:
            params["name"] = name
        if exact_match:
            params["exactMatch"] = "true"

        async for folder in AsyncAlbertPaginator(
            session=self._session,
            path=self.base_path,
            deserialize=lambda item: ChatFolder(**item),
            params=params,
            max_items=max_items,
        ):
            yield folder

    @validate_call
    async def update(
        self,
        *,
        id: str,
        name: str | None = None,
        sequence: list[str] | None = None,
    ) -> ChatFolder:
        """
        Update a chat folder.

        Parameters
        ----------
        id : str
            The ID of the folder to update.
        name : str | None, optional
            New display name for the folder.
        sequence : list | None, optional
            New ordering of child sessions or folders.

        Returns
        -------
        ChatFolder
            The updated folder.

        Notes
        -----
        The following fields can be updated: ``name``, ``sequence``.
        """
        data = []
        if name is not None:
            data.append({"operation": "update", "attribute": "name", "newValue": name})
        if sequence is not None:
            data.append({"operation": "update", "attribute": "sequence", "newValue": sequence})
        if not data:
            return await self.get_by_id(id=id)
        await self._session.patch(f"{self.base_path}/{id}", json={"data": data})
        return await self.get_by_id(id=id)

    @validate_call
    async def delete(self, *, id: str) -> None:
        """
        Delete a chat folder by ID.

        Parameters
        ----------
        id : str
            The ID of the folder to delete.

        Returns
        -------
        None
        """
        await self._session.delete(f"{self.base_path}/{id}")
