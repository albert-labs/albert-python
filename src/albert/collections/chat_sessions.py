from __future__ import annotations

from collections.abc import AsyncIterator

from pydantic import validate_call

from albert.core.async_session import AsyncAlbertSession
from albert.core.pagination import AsyncAlbertPaginator
from albert.resources.chats import ChatSession


class ChatSessionCollection:
    """
    Async collection for managing chat sessions.

    Parameters
    ----------
    session : AsyncAlbertSession
        The Albert async session instance.

    Attributes
    ----------
    base_path : str
        The base URL for chat session API requests.

    Methods
    -------
    create(session) -> ChatSession
        Creates a new chat session.
    get_by_id(id) -> ChatSession
        Retrieves a chat session by its ID.
    get_by_source_session_id(source_session_id) -> ChatSession
        Retrieves a chat session by its external source session ID.
    get_all(name, exact_match, parent_id, max_items) -> AsyncIterator[ChatSession]
        Iterates over chat sessions with optional filters.
    update(id, ...) -> ChatSession
        Updates a chat session by ID.
    delete(id) -> None
        Deletes a chat session by its ID.
    """

    _api_version = "v3"

    def __init__(self, *, session: AsyncAlbertSession):
        """
        Initializes the ChatSessionCollection with the provided session.

        Parameters
        ----------
        session : AsyncAlbertSession
            The async session used to make API requests.
        """
        self._session = session
        self.base_path: str = f"/api/{self._api_version}/chats/sessions"

    @validate_call
    async def create(self, *, session: ChatSession) -> ChatSession:
        """
        Create a new chat session.

        Parameters
        ----------
        session : ChatSession
            The session to create.

        Returns
        -------
        ChatSession
            The created session.
        """
        response = await self._session.post(
            self.base_path,
            json=session.model_dump(by_alias=True, exclude_unset=True, mode="json"),
        )
        return ChatSession(**response.json())

    @validate_call
    async def get_by_id(self, *, id: str) -> ChatSession:
        """
        Retrieve a chat session by its ID.

        Parameters
        ----------
        id : str
            The session ID.

        Returns
        -------
        ChatSession
            The matching session.
        """
        response = await self._session.get(f"{self.base_path}/{id}")
        return ChatSession(**response.json())

    @validate_call
    async def get_by_source_session_id(self, *, source_session_id: str) -> ChatSession:
        """
        Retrieve a chat session by its external source session ID.

        Parameters
        ----------
        source_session_id : str
            The external source session identifier.

        Returns
        -------
        ChatSession
            The matching session.
        """
        response = await self._session.get(f"{self.base_path}/source/{source_session_id}")
        return ChatSession(**response.json())

    async def get_all(
        self,
        *,
        name: list[str] | None = None,
        exact_match: bool = False,
        parent_id: str | None = None,
        max_items: int | None = None,
    ) -> AsyncIterator[ChatSession]:
        """
        Iterate over chat sessions with optional filters.

        Parameters
        ----------
        name : list[str] | None, optional
            Filter by session name(s).
        exact_match : bool, optional
            Whether name filtering uses exact matching (default False).
        parent_id : str | None, optional
            Filter sessions by folder ID.
        max_items : int | None, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Yields
        ------
        ChatSession
            Sessions matching the given filters.
        """
        params: dict = {}
        if name:
            params["name"] = name
        if exact_match:
            params["exactMatch"] = "true"
        if parent_id is not None:
            params["parentId"] = parent_id

        async for session in AsyncAlbertPaginator(
            session=self._session,
            path=self.base_path,
            deserialize=lambda item: ChatSession(**item),
            params=params,
            max_items=max_items,
        ):
            yield session

    @validate_call
    async def update(
        self,
        *,
        id: str,
        name: str | None = None,
        parent_id: str | None = None,
    ) -> ChatSession:
        """
        Update a chat session.

        Parameters
        ----------
        id : str
            The ID of the session to update.
        name : str | None, optional
            New display name for the session.
        parent_id : str | None, optional
            New parent folder ID for the session.

        Returns
        -------
        ChatSession
            The updated session.

        Notes
        -----
        The following fields can be updated: ``name``, ``parent_id``.
        """
        data = []
        if name is not None:
            data.append({"operation": "update", "attribute": "name", "newValue": name})
        if parent_id is not None:
            data.append({"operation": "update", "attribute": "parentId", "newValue": parent_id})
        await self._session.patch(f"{self.base_path}/{id}", json={"data": data})
        return await self.get_by_id(id=id)

    @validate_call
    async def delete(self, *, id: str) -> None:
        """
        Delete a chat session by ID.

        Parameters
        ----------
        id : str
            The ID of the session to delete.

        Returns
        -------
        None
        """
        await self._session.delete(f"{self.base_path}/{id}")
