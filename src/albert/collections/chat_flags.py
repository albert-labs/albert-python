from __future__ import annotations

from pydantic import validate_call

from albert.core.async_session import AsyncAlbertSession
from albert.resources.chats import ChatComponentType, ChatFlag, ChatFlagsInMessage, ChatFlagType


class ChatFlagCollection:
    """Manage flags on "Ask Albert" chat messages (🧪 Beta).

    A chat flag ([`ChatFlag`][albert.resources.chats.ChatFlag]) is a marker set on a
    single message turn in a conversation with Albert's AI assistant, used chiefly
    to capture feedback and interaction state. A message can be flagged as
    starred, downloaded, requested, or hallucinated (see
    [`ChatFlagType`][albert.resources.chats.ChatFlagType]). Flags reference a message by
    its session, request, and sequence, the same coordinates used by
    [`ChatMessageCollection`][albert.collections.chat_messages.ChatMessageCollection].

    This is an async collection accessed as ``client.chat_flags`` on an
    [`AsyncAlbert`][albert.client.AsyncAlbert] client.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    Parameters
    ----------
    session : AsyncAlbertSession
        The authenticated Albert async session used for API calls.

    Methods
    -------
    get_all(type) -> list[ChatFlag]
        List all flagged messages of a given flag type.
    get_by_message(session_id, source_request_id, sequence=None) -> ChatFlagsInMessage
        Retrieve all flags set on a specific message.
    add(session_id, source_request_id, sequence, type, component_type=None) -> ChatFlag
        Add a flag to a message.
    remove(session_id, source_request_id, sequence, type, component_type=None) -> None
        Remove a flag from a message.

    !!! example
        ```python
        from albert import AsyncAlbert
        from albert.resources.chats import ChatFlagType

        async with AsyncAlbert() as client:
            await client.chat_flags.add(
                session_id="<session id>",
                source_request_id="<request id>",
                sequence="000",
                type=ChatFlagType.STARRED,
            )
            starred = await client.chat_flags.get_all(type=ChatFlagType.STARRED)
        ```
    """

    _api_version = "v3"

    def __init__(self, *, session: AsyncAlbertSession):
        """
        Initializes the ChatFlagCollection with the provided session.

        Parameters
        ----------
        session : AsyncAlbertSession
            The async session used to make API requests.
        """
        self._session = session
        self._flags_base = f"/api/{self._api_version}/chats/flags"
        self._sessions_base = f"/api/{self._api_version}/chats/sessions"

    @validate_call
    async def get_all(self, *, type: ChatFlagType) -> list[ChatFlag]:
        """List all flagged messages of a given type.

        Returns flag records for the given
        [`ChatFlagType`][albert.resources.chats.ChatFlagType] across ALL sessions the
        authenticated user can access (not a single session). Each record is a
        pointer, not the full message body: ``parent_id`` (session id),
        ``source_request_id``, ``sequence``, and an optional ``component_type``.

        Parameters
        ----------
        type : ChatFlagType
            The flag type to filter by.

        Returns
        -------
        list[ChatFlag]
            Flagged messages matching the given type.

        !!! example
            ```python
            from albert import AsyncAlbert
            from albert.resources.chats import ChatFlagType

            async with AsyncAlbert() as client:
                starred = await client.chat_flags.get_all(type=ChatFlagType.STARRED)
            ```
        """
        response = await self._session.get(self._flags_base, params={"type": type.value})
        data = response.json()
        return [ChatFlag(**item) for item in data.get("Items", [])]

    @validate_call
    async def get_by_message(
        self,
        *,
        session_id: str,
        source_request_id: str,
        sequence: str | None = None,
    ) -> ChatFlagsInMessage:
        """Retrieve all flags set on a specific message.

        Parameters
        ----------
        session_id : str
            The ID of the parent [`ChatSession`][albert.resources.chats.ChatSession].
        source_request_id : str
            The request trace identifier of the message.
        sequence : str | None, optional
            The zero-padded sequence of the message within the session
            (e.g. ``"000"``).

        Returns
        -------
        ChatFlagsInMessage
            A summary of the flag types set on the message.

        !!! example
            ```python
            from albert import AsyncAlbert

            async with AsyncAlbert() as client:
                flags = await client.chat_flags.get_by_message(
                    session_id="...",
                    source_request_id="...",
                    sequence="000",
                )
            ```
        """
        url = f"{self._sessions_base}/{session_id}/messages/{source_request_id}/flag"
        params: dict[str, str] = {}
        if sequence is not None:
            params["sequence"] = sequence
        response = await self._session.get(url, params=params)
        return ChatFlagsInMessage(**response.json())

    @validate_call
    async def add(
        self,
        *,
        session_id: str,
        source_request_id: str,
        sequence: str,
        type: ChatFlagType,
        component_type: ChatComponentType | None = None,
    ) -> ChatFlag:
        """Add a flag to a message.

        Parameters
        ----------
        session_id : str
            The ID of the parent [`ChatSession`][albert.resources.chats.ChatSession].
        source_request_id : str
            The request trace identifier of the message.
        sequence : str
            The zero-padded sequence of the message within the session
            (e.g. ``"000"``).
        type : ChatFlagType
            The flag type to add.
        component_type : ChatComponentType | None, optional
            Narrow the flag to a single
            [`ChatComponentType`][albert.resources.chats.ChatComponentType] when a request holds
            more than one component.

        Returns
        -------
        ChatFlag
            The created flag.

        !!! example
            ```python
            from albert import AsyncAlbert
            from albert.resources.chats import ChatFlagType

            async with AsyncAlbert() as client:
                flag = await client.chat_flags.add(
                    session_id="...",
                    source_request_id="...",
                    sequence="000",
                    type=ChatFlagType.STARRED,
                )
            ```
        """
        url = f"{self._sessions_base}/{session_id}/messages/{source_request_id}/flag"
        params: dict[str, str] = {"sequence": sequence, "type": type.value}
        if component_type is not None:
            params["componentType"] = component_type.value
        response = await self._session.post(url, params=params)
        return ChatFlag(**response.json())

    @validate_call
    async def remove(
        self,
        *,
        session_id: str,
        source_request_id: str,
        sequence: str,
        type: ChatFlagType,
        component_type: ChatComponentType | None = None,
    ) -> None:
        """Remove a flag from a message.

        Parameters
        ----------
        session_id : str
            The ID of the parent [`ChatSession`][albert.resources.chats.ChatSession].
        source_request_id : str
            The request trace identifier of the message.
        sequence : str
            The zero-padded sequence of the message within the session
            (e.g. ``"000"``).
        type : ChatFlagType
            The flag type to remove.
        component_type : ChatComponentType | None, optional
            Narrow the removal to a single
            [`ChatComponentType`][albert.resources.chats.ChatComponentType] when a request holds
            more than one component.

        Returns
        -------
        None

        !!! example
            ```python
            from albert import AsyncAlbert
            from albert.resources.chats import ChatFlagType

            async with AsyncAlbert() as client:
                await client.chat_flags.remove(
                    session_id="...",
                    source_request_id="...",
                    sequence="000",
                    type=ChatFlagType.STARRED,
                )
            ```
        """
        url = f"{self._sessions_base}/{session_id}/messages/{source_request_id}/flag"
        params: dict[str, str] = {"sequence": sequence, "type": type.value}
        if component_type is not None:
            params["componentType"] = component_type.value
        await self._session.delete(url, params=params)
