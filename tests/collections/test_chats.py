from contextlib import suppress

import pytest

from albert import AsyncAlbert
from albert.exceptions import NotFoundError
from albert.resources.chats import (
    ChatFolder,
    ChatMessage,
    ChatSession,
)

pytestmark = pytest.mark.xfail(reason="Chat API is not deployed yet.")

# ---------------------------------------------------------------------------
# Chat folders
# ---------------------------------------------------------------------------


async def test_chat_folder_create_and_get_by_id(
    async_client: AsyncAlbert, seeded_folder: ChatFolder
):
    """Test creating a folder and fetching it by ID."""
    fetched = await async_client.chat_folders.get_by_id(id=seeded_folder.id)
    assert fetched.id == seeded_folder.id
    assert fetched.name == seeded_folder.name


async def test_chat_folder_get_all(async_client: AsyncAlbert, seeded_folder: ChatFolder):
    """Test that get_all returns at least the seeded folder."""
    results = [f async for f in async_client.chat_folders.get_all(max_items=50)]
    ids = [f.id for f in results]
    assert seeded_folder.id in ids


# ---------------------------------------------------------------------------
# Chat sessions
# ---------------------------------------------------------------------------


async def test_chat_session_create_and_get_by_id(
    async_client: AsyncAlbert, seeded_session: ChatSession
):
    """Test creating a session and fetching it by ID."""
    fetched = await async_client.chat_sessions.get_by_id(id=seeded_session.id)
    assert fetched.id == seeded_session.id
    assert fetched.name == seeded_session.name


async def test_chat_session_get_by_source_session_id(
    async_client: AsyncAlbert, seed_prefix: str, seeded_folder: ChatFolder
):
    """Test looking up a session via its external source session ID."""
    source_id = f"{seed_prefix}-src"
    session = await async_client.chat_sessions.create(
        session=ChatSession(
            name=f"{seed_prefix} Source Session",
            parent_id=seeded_folder.id,
            source_session_id=source_id,
        )
    )
    try:
        fetched = await async_client.chat_sessions.get_by_source_session_id(
            source_session_id=source_id
        )
        assert fetched.id == session.id
        assert fetched.source_session_id == source_id
    finally:
        with suppress(NotFoundError):
            await async_client.chat_sessions.delete(id=session.id)


async def test_chat_session_get_all(async_client: AsyncAlbert, seeded_session: ChatSession):
    """Test that get_all returns at least the seeded session."""
    results = [s async for s in async_client.chat_sessions.get_all(max_items=50)]
    ids = [s.id for s in results]
    assert seeded_session.id in ids


# ---------------------------------------------------------------------------
# Chat messages
# ---------------------------------------------------------------------------


async def test_chat_message_create_and_get_by_id(
    async_client: AsyncAlbert, seeded_session: ChatSession, seeded_message: ChatMessage
):
    """Test creating a message and fetching it by source_request_id + sequence."""
    fetched = await async_client.chat_messages.get_by_id(
        session_id=seeded_session.id,
        source_request_id=seeded_message.source_request_id,
        sequence=seeded_message.sequence,
    )
    assert fetched.source_request_id == seeded_message.source_request_id


async def test_chat_message_get_all(
    async_client: AsyncAlbert, seeded_session: ChatSession, seeded_message: ChatMessage
):
    """Test that get_all returns at least the seeded message."""
    results = [m async for m in async_client.chat_messages.get_all(session_id=seeded_session.id)]
    ids = [m.source_request_id for m in results]
    assert seeded_message.source_request_id in ids
