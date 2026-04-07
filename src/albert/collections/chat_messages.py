from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from pydantic import validate_call

from albert.core.async_session import AsyncAlbertSession
from albert.core.pagination import AsyncAlbertPaginator
from albert.resources.chats import ChatComponentType, ChatMessage


class ChatMessageCollection:
    """
    Async collection for managing messages within a chat session.

    Parameters
    ----------
    session : AsyncAlbertSession
        The Albert async session instance.

    Methods
    -------
    create(message) -> ChatMessage
        Adds a message to a chat session.
    get_by_id(session_id, source_request_id, sequence, component_type) -> ChatMessage
        Retrieves a single message by its source request ID and sequence.
    get_all(session_id, ...) -> AsyncIterator[ChatMessage]
        Iterates over messages in a session.
    update(session_id, source_request_id, sequence, content) -> ChatMessage
        Updates the content of a message.
    delete(session_id, source_request_id, sequence) -> None
        Deletes a message from a session.
    """

    _api_version = "v3"

    def __init__(self, *, session: AsyncAlbertSession):
        """
        Initializes the ChatMessageCollection with the provided session.

        Parameters
        ----------
        session : AsyncAlbertSession
            The async session used to make API requests.
        """
        self._session = session
        self._sessions_base = f"/api/{self._api_version}/chats/sessions"

    @validate_call
    async def create(self, *, message: ChatMessage) -> ChatMessage:
        """
        Add a message to a chat session.

        Parameters
        ----------
        message : ChatMessage
            The message to create. ``parent_id`` must be set to the session ID.
            ``source_request_id`` is auto-generated if not provided.

        Returns
        -------
        ChatMessage
            The created message.
        """
        payload = message.model_dump(by_alias=True, exclude_unset=True, mode="json")
        # parentId is encoded in the URL path, not the request body
        payload.pop("parentId", None)
        payload.setdefault("sourceRequestId", str(uuid.uuid4()))
        url = f"{self._sessions_base}/{message.parent_id}/messages"
        response = await self._session.post(url, json=payload)
        return ChatMessage(**response.json())

    @validate_call
    async def get_by_id(
        self,
        *,
        session_id: str,
        source_request_id: str,
        sequence: str,
        component_type: ChatComponentType | None = None,
    ) -> ChatMessage:
        """
        Retrieve a single message by its source request ID and sequence.

        Parameters
        ----------
        session_id : str
            The ID of the parent session.
        source_request_id : str
            The request trace identifier of the message.
        sequence : str
            The zero-padded sequence of the message (e.g. "000").
        component_type : ChatComponentType | None, optional
            Narrows the lookup to a specific component type.

        Returns
        -------
        ChatMessage
            The matching message.
        """
        url = f"{self._sessions_base}/{session_id}/messages/{source_request_id}"
        params: dict = {"sequence": sequence}
        if component_type is not None:
            params["componentType"] = component_type.value
        response = await self._session.get(url, params=params)
        return ChatMessage(**response.json())

    async def get_all(
        self,
        *,
        session_id: str,
        max_items: int | None = None,
    ) -> AsyncIterator[ChatMessage]:
        """
        Iterate over messages in a session.

        Parameters
        ----------
        session_id : str
            The ID of the session whose messages to list.
        max_items : int | None, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Yields
        ------
        ChatMessage
            Messages in the session, oldest first.
        """
        url = f"{self._sessions_base}/{session_id}/messages"
        async for message in AsyncAlbertPaginator(
            session=self._session,
            path=url,
            deserialize=lambda item: ChatMessage(**item),
            max_items=max_items,
        ):
            yield message

    @validate_call
    async def update(
        self,
        *,
        session_id: str,
        source_request_id: str,
        sequence: str,
        content: str | dict,
    ) -> ChatMessage:
        """
        Update the content of a message.

        Parameters
        ----------
        session_id : str
            The ID of the parent session.
        source_request_id : str
            The request trace identifier of the message.
        sequence : str
            The zero-padded sequence of the message (e.g. "000").
        content : str | dict
            The new content for the message.

        Returns
        -------
        ChatMessage
            The updated message.

        Notes
        -----
        The following fields can be updated: ``content``.
        """
        url = f"{self._sessions_base}/{session_id}/messages/{source_request_id}"
        payload = {"data": [{"operation": "update", "attribute": "Content", "newValue": content}]}
        await self._session.patch(url, params={"sequence": sequence}, json=payload)
        return await self.get_by_id(
            session_id=session_id,
            source_request_id=source_request_id,
            sequence=sequence,
        )

    @validate_call
    async def delete(
        self,
        *,
        session_id: str,
        source_request_id: str,
        sequence: str,
    ) -> None:
        """
        Delete a message from a session.

        Parameters
        ----------
        session_id : str
            The ID of the parent session.
        source_request_id : str
            The request trace identifier of the message.
        sequence : str
            The zero-padded sequence of the message (e.g. "000").

        Returns
        -------
        None
        """
        url = f"{self._sessions_base}/{session_id}/messages/{source_request_id}"
        await self._session.delete(url, params={"sequence": sequence})
