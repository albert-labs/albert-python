from __future__ import annotations

from collections.abc import AsyncIterator

from pydantic import GetCoreSchemaHandler, validate_call
from pydantic_core import core_schema

from albert.core.async_session import AsyncAlbertSession
from albert.core.pagination import AsyncAlbertPaginator
from albert.resources.chats import ChatSession


class _UnsetType:
    """Sentinel type for distinguishing unset parameters from explicit None."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: object, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.is_instance_schema(cls)


_UNSET = _UnsetType()


class ChatSessionCollection:
    """Manage "Ask Albert" chat sessions in the Albert platform (🧪 Beta).

    A chat session is a single conversation with Albert's AI assistant, "Ask
    Albert". Each session ([`ChatSession`][albert.resources.chats.ChatSession]) holds an
    ordered series of message turns
    ([`ChatMessage`][albert.resources.chats.ChatMessage], managed by
    [`ChatMessageCollection`][albert.collections.chat_messages.ChatMessageCollection]) and can be
    filed under a folder
    ([`ChatFolder`][albert.resources.chats.ChatFolder], managed by
    [`ChatFolderCollection`][albert.collections.chat_folders.ChatFolderCollection]).

    This is an async collection accessed as ``client.chat_sessions`` on an
    [`AsyncAlbert`][albert.client.AsyncAlbert] client.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    Parameters
    ----------
    session : AsyncAlbertSession
        The authenticated Albert async session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for chat session requests.

    Methods
    -------
    create(session) -> ChatSession
        Create a new chat session.
    get_by_id(id) -> ChatSession
        Retrieve a single session by its ID.
    get_by_source_session_id(source_session_id) -> ChatSession
        Retrieve a session by its external source session ID.
    get_all(name, exact_match, parent_id, max_items) -> AsyncIterator[ChatSession]
        Iterate over sessions, with optional filters.
    update(id, name=None, parent_id=...) -> ChatSession
        Rename a session or move it between folders.
    delete(id) -> None
        Delete a session by its ID.

    !!! example
        ```python
        from albert import AsyncAlbert
        from albert.resources.chats import ChatSession

        async with AsyncAlbert() as client:
            session = await client.chat_sessions.create(
                session=ChatSession(name="Titanium dioxide questions", source_session_id="ext-123")
            )
            async for s in client.chat_sessions.get_all(name=["titanium"]):
                print(s.id, s.name)
        ```
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
        """Create a new chat session.

        Parameters
        ----------
        session : ChatSession
            The session to create. ``name`` and ``source_session_id`` are required;
            set ``parent_id`` to file the session under a
            [`ChatFolder`][albert.resources.chats.ChatFolder].

        Returns
        -------
        ChatSession
            The created session, populated with its server-assigned ``id``.

        !!! example
            ```python
            from albert import AsyncAlbert
            from albert.resources.chats import ChatSession

            async with AsyncAlbert() as client:
                session = await client.chat_sessions.create(
                    session=ChatSession(name="Titanium dioxide questions", source_session_id="...")
                )
            ```
        """
        response = await self._session.post(
            self.base_path,
            json=session.model_dump(by_alias=True, exclude_unset=True, mode="json"),
        )
        return ChatSession(**response.json())

    @validate_call
    async def get_by_id(self, *, id: str) -> ChatSession:
        """Retrieve a chat session by its ID.

        Parameters
        ----------
        id : str
            The identifier of the session to retrieve.

        Returns
        -------
        ChatSession
            The matching session.

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                session = await client.chat_sessions.get_by_id(id="...")
            ```
        """
        response = await self._session.get(f"{self.base_path}/{id}")
        return ChatSession(**response.json())

    @validate_call
    async def get_by_source_session_id(self, *, source_session_id: str) -> ChatSession:
        """Retrieve a chat session by its external source session ID.

        Use this to look up a session by the identifier that links it to a source
        system, rather than by its Albert ``id``.

        Parameters
        ----------
        source_session_id : str
            The external source session identifier (the session's
            ``source_session_id``).

        Returns
        -------
        ChatSession
            The matching session.

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                session = await client.chat_sessions.get_by_source_session_id(source_session_id="...")
            ```
        """
        response = await self._session.get(f"{self.base_path}/source/{source_session_id}")
        return ChatSession(**response.json())

    @validate_call
    async def get_all(
        self,
        *,
        name: list[str] | None = None,
        exact_match: bool = False,
        parent_id: str | None = None,
        max_items: int | None = None,
    ) -> AsyncIterator[ChatSession]:
        """Iterate over chat sessions, with optional filters.

        Transparently pages through results, yielding one session at a time.

        Parameters
        ----------
        name : list[str] | None, optional
            Filter to sessions whose name matches any of the given values.
        exact_match : bool, optional
            When ``True``, ``name`` must match exactly; otherwise it matches as a
            substring. Defaults to ``False``.
        parent_id : str | None, optional
            Filter to sessions filed under the given
            [`ChatFolder`][albert.resources.chats.ChatFolder].
        max_items : int | None, optional
            Maximum number of sessions to yield in total. If ``None``, yields all
            matching sessions.

        Yields
        ------
        ChatSession
            Sessions matching the given filters.

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                async for session in client.chat_sessions.get_all(name=["titanium"]):
                    print(session.id, session.name)
            ```
        """
        params: dict[str, str | list[str]] = {}
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
        parent_id: str | None | _UnsetType = _UNSET,
    ) -> ChatSession:
        """Update a chat session.

        Rename a session and/or move it between folders. Only the arguments you
        pass are changed; omitted arguments are left untouched.

        Parameters
        ----------
        id : str
            The identifier of the session to update.
        name : str | None, optional
            A new display name for the session.
        parent_id : str | None, optional
            The [`ChatFolder`][albert.resources.chats.ChatFolder] to move the session
            into. Pass ``None`` to remove the session from its current folder. When
            omitted entirely, the folder is left unchanged.

        Returns
        -------
        ChatSession
            The updated session.

        Notes
        -----
        The following fields can be updated: ``name``, ``parent_id``.

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                session = await client.chat_sessions.update(id="...", name="Renamed session")
            ```
        """
        data = []
        if name is not None:
            data.append({"operation": "update", "attribute": "name", "newValue": name})
        if parent_id is not _UNSET:
            data.append({"operation": "update", "attribute": "parentId", "newValue": parent_id})
        if not data:
            return await self.get_by_id(id=id)
        await self._session.patch(f"{self.base_path}/{id}", json={"data": data})
        return await self.get_by_id(id=id)

    @validate_call
    async def delete(self, *, id: str) -> None:
        """Delete a chat session by ID.

        Parameters
        ----------
        id : str
            The identifier of the session to delete.

        Returns
        -------
        None

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                await client.chat_sessions.delete(id="...")
            ```
        """
        await self._session.delete(f"{self.base_path}/{id}")
