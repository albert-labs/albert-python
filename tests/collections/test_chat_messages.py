import uuid

import pytest

from albert.resources.chats import (
    ChatComponentType,
    ChatMessage,
    ChatRole,
    ChatUserType,
)


@pytest.mark.asyncio
async def test_chat_message_page_context_round_trip(async_client, seeded_session) -> None:
    """Test page_context persists on create and reloads on get_by_id."""
    page_context = {
        "url": "https://app.albertinvent.com/#notebook",
        "entity": "notebook",
        "albert_id": "NTB1",
    }
    source_request_id = str(uuid.uuid4())

    await async_client.chat_messages.create(
        message=ChatMessage(
            component_type=ChatComponentType.TEXT,
            user_type=ChatUserType.USER,
            role=ChatRole.USER,
            content="hello with page context",
            parent_id=seeded_session.id,
            source_request_id=source_request_id,
            sequence="001",
            page_context=page_context,
        )
    )

    fetched = await async_client.chat_messages.get_by_id(
        session_id=seeded_session.id,
        source_request_id=source_request_id,
        sequence="001",
        component_type=ChatComponentType.TEXT,
    )

    assert fetched.page_context == page_context
