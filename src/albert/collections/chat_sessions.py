from __future__ import annotations

from collections.abc import AsyncIterator

from pydantic import validate_call

from albert.core.async_session import AsyncAlbertSession
from albert.core.pagination import AsyncAlbertPaginator
from albert.resources.chats import ChatSession


class ChatSessionCollection:
    """Async collection for managing chat sessions."""

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
        created_by: str | None = None,
        updated_by: str | None = None,
        exact_match: bool = False,
        max_items: int | None = None,
    ) -> AsyncIterator[ChatSession]:
        """
        Iterate over chat sessions with optional filters.

        Parameters
        ----------
        name : list[str] | None, optional
            Filter by session name(s).
        created_by : str | None, optional
            Filter by the user who created the session.
        updated_by : str | None, optional
            Filter by the user who last updated the session.
        exact_match : bool, optional
            Whether name filtering uses exact matching (default False).
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
        if created_by is not None:
            params["createdBy"] = created_by
        if updated_by is not None:
            params["updatedBy"] = updated_by
        if exact_match:
            params["exactMatch"] = "true"

        async for session in AsyncAlbertPaginator(
            session=self._session,
            path=self.base_path,
            deserialize=lambda item: ChatSession(**item),
            params=params,
            max_items=max_items,
        ):
            yield session

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
