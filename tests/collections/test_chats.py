import pytest_asyncio

from albert import AsyncAlbert
from albert.resources.chats import (
    ChatComponentType,
    ChatFolder,
    ChatMessage,
    ChatRole,
    ChatSession,
    ChatUserType,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def seeded_folder(async_client: AsyncAlbert, seed_prefix: str) -> ChatFolder:
    return await async_client.chat_folders.create(
        folder=ChatFolder(name=f"{seed_prefix} Chat Folder")
    )


@pytest_asyncio.fixture(scope="function")
async def seeded_session(
    async_client: AsyncAlbert, seed_prefix: str, seeded_folder: ChatFolder
) -> ChatSession:
    return await async_client.chat_sessions.create(
        session=ChatSession(name=f"{seed_prefix} Chat Session", parent_id=seeded_folder.id)
    )


@pytest_asyncio.fixture(scope="function")
async def seeded_message(async_client: AsyncAlbert, seeded_session: ChatSession) -> ChatMessage:
    return await async_client.chat_messages.create(
        message=ChatMessage(
            component_type=ChatComponentType.TEXT,
            user_type=ChatUserType.USER,
            role=ChatRole.USER,
            content={"message": "Hello from SDK tests"},
            parent_id=seeded_session.id,
            sequence="000",
        )
    )


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
    fetched = await async_client.chat_sessions.get_by_source_session_id(
        source_session_id=source_id
    )
    assert fetched.id == session.id
    assert fetched.source_session_id == source_id


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
