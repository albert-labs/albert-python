from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from pydantic import validate_call

from albert.core.async_session import AsyncAlbertSession
from albert.core.pagination import AsyncAlbertPaginator
from albert.resources.chats import ChatComponentType, ChatMessage


class ChatMessageCollection:
    """Manage the message turns within an "Ask Albert" chat session (🧪 Beta).

    A chat message ([`ChatMessage`][albert.resources.chats.ChatMessage]) is one turn, or
    turn component, of a conversation with Albert's AI assistant. Messages always
    belong to a parent session
    ([`ChatSession`][albert.resources.chats.ChatSession], managed by
    [`ChatSessionCollection`][albert.collections.chat_sessions.ChatSessionCollection]), so every
    method here takes a ``session_id``. Within a session a message is addressed by
    the pair ``(source_request_id, sequence)``, and
    [`ChatComponentType`][albert.resources.chats.ChatComponentType] distinguishes components
    that share a request.

    This is an async collection accessed as ``client.chat_messages`` on an
    [`AsyncAlbert`][albert.client.AsyncAlbert] client.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    !!! example
        ```python
        from albert import AsyncAlbert
        from albert.resources.chats import ChatMessage, ChatComponentType, ChatUserType, ChatRole

        async with AsyncAlbert() as client:
            await client.chat_messages.create(
                message=ChatMessage(
                    parent_id="<session id>",
                    component_type=ChatComponentType.TEXT,
                    user_type=ChatUserType.USER,
                    role=ChatRole.USER,
                    content="What raw materials contain titanium dioxide?",
                )
            )
            async for message in client.chat_messages.get_all(session_id="<session id>"):
                print(message.sequence, message.content)
        ```

    Parameters
    ----------
    session : AsyncAlbertSession
        The authenticated Albert async session used for API calls.

    Methods
    -------
    create(message) -> ChatMessage
        Add a message to a chat session.
    get_by_id(session_id, source_request_id, sequence, component_type=None) -> ChatMessage
        Get a single message by its request ID and sequence.
    get_all(session_id, max_items=None) -> AsyncIterator[ChatMessage]
        Iterate over the messages in a session, oldest first.
    update(session_id, source_request_id, sequence, content) -> ChatMessage
        Update the content of a message.
    delete(session_id, source_request_id, sequence) -> None
        Delete a message from a session.
    """

    _api_version = "v3"

    def __init__(self, *, session: AsyncAlbertSession):
        """Initialize a ChatMessageCollection.

        Parameters
        ----------
        session : AsyncAlbertSession
            The authenticated Albert async session used for API calls.
        """
        self._session = session
        self._sessions_base = f"/api/{self._api_version}/chats/sessions"

    @validate_call
    async def create(self, *, message: ChatMessage) -> ChatMessage:
        """Add a message to a chat session.

        !!! example
            ```python
            from albert import AsyncAlbert
            from albert.resources.chats import ChatMessage, ChatComponentType, ChatUserType, ChatRole

            async with AsyncAlbert() as client:
                message = await client.chat_messages.create(
                    message=ChatMessage(
                        parent_id="...",
                        component_type=ChatComponentType.TEXT,
                        user_type=ChatUserType.USER,
                        role=ChatRole.USER,
                        content="What raw materials contain titanium dioxide?",
                    )
                )
            ```

        Parameters
        ----------
        message : ChatMessage
            The message to create. ``parent_id`` must be set to the target
            [`ChatSession`][albert.resources.chats.ChatSession] ID. ``source_request_id``
            is auto-generated when not provided.

        Returns
        -------
        ChatMessage
            The created message.

        Notes
        -----
        The create response does not currently echo the message ``content``, so the
        returned object's ``content`` may be ``None``. Use [`get_by_id`][albert.collections.chat_messages.ChatMessageCollection.get_by_id] to read
        the stored message back in full.
        """
        payload = message.model_dump(by_alias=True, exclude_unset=True, mode="json")
        # parentId is encoded in the URL path, not the request body
        payload.pop("parentId", None)
        payload.setdefault("sourceRequestId", str(uuid.uuid4()))
        url = f"{self._sessions_base}/{message.parent_id}/messages"
        response = await self._session.post(url, json=payload)
        # TODO(backend): POST /sessions/{id}/messages response does not include the
        # Content field, so message.content will be None after create. The create
        # response should mirror the full message object including Content so callers
        # don't need a follow-up get_by_id to access the payload they just sent.
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
        """Get a single message by its request ID and sequence.

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                message = await client.chat_messages.get_by_id(
                    session_id="...",
                    source_request_id="...",
                    sequence="000",
                )
            ```

        Parameters
        ----------
        session_id : str
            The ID of the parent [`ChatSession`][albert.resources.chats.ChatSession].
        source_request_id : str
            The request trace identifier of the message.
        sequence : str
            The zero-padded sequence of the message within the session
            (e.g. ``"000"``).
        component_type : ChatComponentType | None, optional
            Narrow the lookup to a single
            [`ChatComponentType`][albert.resources.chats.ChatComponentType] when a request holds
            more than one component.

        Returns
        -------
        ChatMessage
            The fully populated message.
        """
        url = f"{self._sessions_base}/{session_id}/messages/{source_request_id}"
        params: dict = {"sequence": sequence}
        if component_type is not None:
            params["componentType"] = component_type.value
        response = await self._session.get(url, params=params)
        return ChatMessage(**response.json())

    @validate_call
    def get_all(
        self,
        *,
        session_id: str,
        max_items: int | None = None,
    ) -> AsyncIterator[ChatMessage]:
        """Iterate over the messages in a session, oldest first.

        Transparently pages through results, yielding one message at a time.
        Returns the paginator directly so ``has_more`` remains available.

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                async for message in client.chat_messages.get_all(session_id="..."):
                    print(message.sequence, message.content)
            ```

        Parameters
        ----------
        session_id : str
            The ID of the [`ChatSession`][albert.resources.chats.ChatSession] whose
            messages to list.
        max_items : int | None, optional
            Maximum number of messages to yield in total. If ``None``, yields every
            message in the session.

        Returns
        -------
        AsyncIterator[ChatMessage]
            Messages in the session, oldest first.
        """
        url = f"{self._sessions_base}/{session_id}/messages"
        return AsyncAlbertPaginator(
            session=self._session,
            path=url,
            deserialize=lambda item: ChatMessage(**item),
            max_items=max_items,
        )

    @validate_call
    async def update(
        self,
        *,
        session_id: str,
        source_request_id: str,
        sequence: str,
        content: str | dict,
    ) -> ChatMessage:
        """Update the content of a message.

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                message = await client.chat_messages.update(
                    session_id="...",
                    source_request_id="...",
                    sequence="000",
                    content="Updated message text",
                )
            ```

        Parameters
        ----------
        session_id : str
            The ID of the parent [`ChatSession`][albert.resources.chats.ChatSession].
        source_request_id : str
            The request trace identifier of the message.
        sequence : str
            The zero-padded sequence of the message within the session
            (e.g. ``"000"``).
        content : str | dict
            The new content for the message. Use a string for text components or an
            object for richer components, matching the message's
            [`ChatComponentType`][albert.resources.chats.ChatComponentType].

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
        """Delete a message from a session.

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                await client.chat_messages.delete(
                    session_id="...",
                    source_request_id="...",
                    sequence="000",
                )
            ```

        Parameters
        ----------
        session_id : str
            The ID of the parent [`ChatSession`][albert.resources.chats.ChatSession].
        source_request_id : str
            The request trace identifier of the message.
        sequence : str
            The zero-padded sequence of the message within the session
            (e.g. ``"000"``).

        Returns
        -------
        None
        """
        url = f"{self._sessions_base}/{session_id}/messages/{source_request_id}"
        await self._session.delete(url, params={"sequence": sequence})
