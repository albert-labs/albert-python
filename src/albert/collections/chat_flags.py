from __future__ import annotations

from pydantic import validate_call

from albert.core.async_session import AsyncAlbertSession
from albert.resources.chats import ChatComponentType, ChatFlag, ChatFlagsInMessage, ChatFlagType


class ChatFlagCollection:
    """
    Async collection for managing flags on chat messages.

    Flags allow users to mark messages as starred, downloaded, requested, or hallucinated.

    Parameters
    ----------
    session : AsyncAlbertSession
        The Albert async session instance.

    Methods
    -------
    get_all(type) -> list[ChatFlag]
        Lists all flagged messages of a given flag type.
    get_by_message(session_id, source_request_id, sequence) -> ChatFlagsInMessage
        Retrieves all flags set on a specific message.
    add(session_id, source_request_id, sequence, type, component_type) -> ChatFlag
        Adds a flag to a message.
    remove(session_id, source_request_id, sequence, type, component_type) -> None
        Removes a flag from a message.
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
        """
        List all flagged messages of a given type.

        Parameters
        ----------
        type : ChatFlagType
            The type of flag to filter by.

        Returns
        -------
        list[ChatFlag]
            Flagged messages matching the given type.
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
        """
        Retrieve all flags set on a specific message.

        Parameters
        ----------
        session_id : str
            The ID of the parent session.
        source_request_id : str
            The request trace identifier of the message.
        sequence : str | None, optional
            The zero-padded sequence of the message.

        Returns
        -------
        ChatFlagsInMessage
            The flags set on the message.
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
        """
        Add a flag to a message.

        Parameters
        ----------
        session_id : str
            The ID of the parent session.
        source_request_id : str
            The request trace identifier of the message.
        sequence : str
            The zero-padded sequence of the message.
        type : ChatFlagType
            The type of flag to add.
        component_type : ChatComponentType | None, optional
            Narrows the flag to a specific component type.

        Returns
        -------
        ChatFlag
            The created flag.
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
        """
        Remove a flag from a message.

        Parameters
        ----------
        session_id : str
            The ID of the parent session.
        source_request_id : str
            The request trace identifier of the message.
        sequence : str
            The zero-padded sequence of the message.
        type : ChatFlagType
            The type of flag to remove.
        component_type : ChatComponentType | None, optional
            Narrows the removal to a specific component type.

        Returns
        -------
        None
        """
        url = f"{self._sessions_base}/{session_id}/messages/{source_request_id}/flag"
        params: dict[str, str] = {"sequence": sequence, "type": type.value}
        if component_type is not None:
            params["componentType"] = component_type.value
        await self._session.delete(url, params=params)
