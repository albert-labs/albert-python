import uuid
from contextlib import suppress

from albert.client import AsyncAlbert
from albert.exceptions import NotFoundError
from albert.resources.chats import (
    ChatComponentType,
    ChatMessage,
    ChatRole,
    ChatSession,
    ChatUserType,
)


async def test_get_all_filters_by_source_request_id(
    async_client: AsyncAlbert, seed_prefix: str
) -> None:
    """Test get_all returns only messages for the given source request ID."""
    session: ChatSession | None = None
    try:
        session = await async_client.chat_sessions.create(
            session=ChatSession(
                name=f"{seed_prefix} message filter",
                source_session_id=str(uuid.uuid4()),
            )
        )
        assert session.id is not None
        for source_request_id, sequence in (
            ("REQ_SELECTED", "000"),
            ("REQ_SELECTED", "001"),
            ("REQ_EXCLUDED", "000"),
        ):
            await async_client.chat_messages.create(
                message=ChatMessage(
                    parent_id=session.id,
                    source_request_id=source_request_id,
                    sequence=sequence,
                    component_type=ChatComponentType.TEXT,
                    user_type=ChatUserType.USER,
                    role=ChatRole.USER,
                    content=f"{source_request_id} {sequence}",
                )
            )

        messages = [
            message
            async for message in async_client.chat_messages.get_all(
                session_id=session.id, source_request_id="REQ_SELECTED"
            )
        ]

        assert [(message.source_request_id, message.sequence) for message in messages] == [
            ("REQ_SELECTED", "000"),
            ("REQ_SELECTED", "001"),
        ]
    finally:
        if session is not None and session.id is not None:
            with suppress(NotFoundError):
                await async_client.chat_sessions.delete(id=session.id)
