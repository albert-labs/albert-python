from __future__ import annotations

from collections.abc import AsyncIterator

from pydantic import validate_call

from albert.core.async_session import AsyncAlbertSession
from albert.core.pagination import AsyncAlbertPaginator
from albert.resources.chats import ChatFolder


class ChatFolderCollection:
    """Manage folders that organize "Ask Albert" chat sessions (🧪 Beta).

    A chat folder ([`ChatFolder`][albert.resources.chats.ChatFolder]) groups related
    conversations with Albert's AI assistant. Sessions
    ([`ChatSession`][albert.resources.chats.ChatSession], managed by
    [`ChatSessionCollection`][albert.collections.chat_sessions.ChatSessionCollection]) are filed
    under a folder via the session's ``parent_id``, and folders can be nested
    inside one another.

    This is an async collection accessed as ``client.chat_folders`` on an
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
        The base API route for chat folder requests.

    Methods
    -------
    create(folder) -> ChatFolder
        Create a new chat folder.
    get_by_id(id) -> ChatFolder
        Retrieve a single folder by its ID.
    get_all(name, exact_match, max_items) -> AsyncIterator[ChatFolder]
        Iterate over folders, with optional filters.
    update(id, name=None, sequence=None) -> ChatFolder
        Rename a folder or reorder its contents.
    delete(id) -> None
        Delete a folder by its ID.

    !!! example
        ```python
        from albert import AsyncAlbert
        from albert.resources.chats import ChatFolder

        async with AsyncAlbert() as client:
            folder = await client.chat_folders.create(
                folder=ChatFolder(name="Formulation questions")
            )
            async for f in client.chat_folders.get_all():
                print(f.id, f.name)
        ```
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
        """Create a new chat folder.

        Parameters
        ----------
        folder : ChatFolder
            The folder to create. ``name`` is required; set ``parent_id`` to nest
            the folder inside another folder.

        Returns
        -------
        ChatFolder
            The created folder, populated with its server-assigned ``id``.

        !!! example
            ```python
            from albert import AsyncAlbert
            from albert.resources.chats import ChatFolder

            async with AsyncAlbert() as client:
                folder = await client.chat_folders.create(
                    folder=ChatFolder(name="Formulation questions")
                )
            ```
        """
        response = await self._session.post(
            self.base_path,
            json=folder.model_dump(by_alias=True, exclude_unset=True, mode="json"),
        )
        return ChatFolder(**response.json())

    @validate_call
    async def get_by_id(self, *, id: str) -> ChatFolder:
        """Retrieve a chat folder by its ID.

        Parameters
        ----------
        id : str
            The identifier of the folder to retrieve.

        Returns
        -------
        ChatFolder
            The matching folder.

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                folder = await client.chat_folders.get_by_id(id="...")
            ```
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
        """Iterate over chat folders, with optional filters.

        Transparently pages through results, yielding one folder at a time.

        Parameters
        ----------
        name : list[str] | None, optional
            Filter to folders whose name matches any of the given values.
        exact_match : bool, optional
            When ``True``, ``name`` must match exactly; otherwise it matches as a
            substring. Defaults to ``False``.
        max_items : int | None, optional
            Maximum number of folders to yield in total. If ``None``, yields all
            matching folders.

        Yields
        ------
        ChatFolder
            Folders matching the given filters.

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                async for folder in client.chat_folders.get_all():
                    print(folder.id, folder.name)
            ```
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
        """Update a chat folder.

        Rename a folder and/or reorder its contents. Only the arguments you pass
        are changed; omitted arguments are left untouched.

        Parameters
        ----------
        id : str
            The identifier of the folder to update.
        name : str | None, optional
            A new display name for the folder.
        sequence : list[str] | None, optional
            A new ordering of the folder's child sessions and folders, given as
            their IDs in the desired order.

        Returns
        -------
        ChatFolder
            The updated folder.

        Notes
        -----
        The following fields can be updated: ``name``, ``sequence``.

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                folder = await client.chat_folders.update(id="...", name="Renamed folder")
            ```
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
        """Delete a chat folder by ID.

        Parameters
        ----------
        id : str
            The identifier of the folder to delete.

        Returns
        -------
        None

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                await client.chat_folders.delete(id="...")
            ```
        """
        await self._session.delete(f"{self.base_path}/{id}")
