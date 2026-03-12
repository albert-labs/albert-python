from __future__ import annotations

from collections.abc import AsyncIterator

from pydantic import validate_call

from albert.core.async_session import AsyncAlbertSession
from albert.core.pagination import AsyncAlbertPaginator
from albert.resources.chats import ChatFolder


class ChatFolderCollection:
    """Async collection for managing chat folders."""

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

    async def get_all(
        self,
        *,
        name: list[str] | None = None,
        created_by: str | None = None,
        updated_by: str | None = None,
        exact_match: bool = False,
        max_items: int | None = None,
    ) -> AsyncIterator[ChatFolder]:
        """
        Iterate over chat folders with optional filters.

        Parameters
        ----------
        name : list[str] | None, optional
            Filter by folder name(s).
        created_by : str | None, optional
            Filter by the user who created the folder.
        updated_by : str | None, optional
            Filter by the user who last updated the folder.
        exact_match : bool, optional
            Whether name filtering uses exact matching (default False).
        max_items : int | None, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Yields
        ------
        ChatFolder
            Folders matching the given filters.
        """
        params: dict = {}
        if name:
            params["name"] = name
        if created_by is not None:
            params["createdBy"] = created_by
        if updated_by is not None:
            params["updatedBy"] = updated_by
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
