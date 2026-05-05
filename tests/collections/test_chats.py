import uuid
from contextlib import suppress

import pytest

from albert import AsyncAlbert
from albert.exceptions import NotFoundError
from albert.resources.chats import (
    ChatComponentType,
    ChatFlagType,
    ChatFolder,
    ChatMessage,
    ChatRole,
    ChatSession,
    ChatUserType,
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
    source_id = str(uuid.uuid4())
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


# ---------------------------------------------------------------------------
# Chat session update
# ---------------------------------------------------------------------------


async def test_chat_session_update(
    async_client: AsyncAlbert, seeded_session: ChatSession, seed_prefix: str
):
    """Test updating a session name."""
    new_name = f"{seed_prefix} Updated Session"
    updated = await async_client.chat_sessions.update(id=seeded_session.id, name=new_name)
    assert updated.name == new_name


async def test_chat_session_get_all_by_parent_id(
    async_client: AsyncAlbert, seeded_session: ChatSession, seeded_folder: ChatFolder
):
    """Test filtering sessions by parent folder ID."""
    results = [
        s
        async for s in async_client.chat_sessions.get_all(parent_id=seeded_folder.id, max_items=50)
    ]
    ids = [s.id for s in results]
    assert seeded_session.id in ids


# ---------------------------------------------------------------------------
# Chat folder update
# ---------------------------------------------------------------------------


async def test_chat_folder_update(
    async_client: AsyncAlbert, seeded_folder: ChatFolder, seed_prefix: str
):
    """Test updating a folder name."""
    new_name = f"{seed_prefix} Updated Folder"
    updated = await async_client.chat_folders.update(id=seeded_folder.id, name=new_name)
    assert updated.name == new_name


# ---------------------------------------------------------------------------
# Chat message update and delete
# ---------------------------------------------------------------------------


async def test_chat_message_update(
    async_client: AsyncAlbert, seeded_session: ChatSession, seeded_message: ChatMessage
):
    """Test updating a message's content."""
    new_content = {"message": "Updated content"}
    updated = await async_client.chat_messages.update(
        session_id=seeded_session.id,
        source_request_id=seeded_message.source_request_id,
        sequence=seeded_message.sequence,
        content=new_content,
    )
    assert updated.content == new_content


async def test_chat_message_delete(async_client: AsyncAlbert, seeded_session: ChatSession):
    """Test deleting a message raises NotFoundError on subsequent lookup."""
    message = await async_client.chat_messages.create(
        message=ChatMessage(
            component_type=ChatComponentType.TEXT,
            user_type=ChatUserType.USER,
            role=ChatRole.USER,
            content={"message": "To be deleted"},
            parent_id=seeded_session.id,
            sequence="001",
        )
    )
    await async_client.chat_messages.delete(
        session_id=seeded_session.id,
        source_request_id=message.source_request_id,
        sequence=message.sequence,
    )
    with pytest.raises(NotFoundError):
        await async_client.chat_messages.get_by_id(
            session_id=seeded_session.id,
            source_request_id=message.source_request_id,
            sequence=message.sequence,
        )


# ---------------------------------------------------------------------------
# Chat flags
# ---------------------------------------------------------------------------


async def test_chat_flag_add_and_get_by_message(
    async_client: AsyncAlbert, seeded_session: ChatSession, seeded_message: ChatMessage
):
    """Test adding a flag and retrieving flags on a message."""
    await async_client.chat_flags.add(
        session_id=seeded_session.id,
        source_request_id=seeded_message.source_request_id,
        sequence=seeded_message.sequence,
        type=ChatFlagType.STARRED,
    )
    try:
        flags_in_message = await async_client.chat_flags.get_by_message(
            session_id=seeded_session.id,
            source_request_id=seeded_message.source_request_id,
            sequence=seeded_message.sequence,
        )
        assert ChatFlagType.STARRED in flags_in_message.flags
    finally:
        with suppress(Exception):
            await async_client.chat_flags.remove(
                session_id=seeded_session.id,
                source_request_id=seeded_message.source_request_id,
                sequence=seeded_message.sequence,
                type=ChatFlagType.STARRED,
            )


async def test_chat_flag_get_all(
    async_client: AsyncAlbert, seeded_session: ChatSession, seeded_message: ChatMessage
):
    """Test that get_all returns flags of the given type."""
    await async_client.chat_flags.add(
        session_id=seeded_session.id,
        source_request_id=seeded_message.source_request_id,
        sequence=seeded_message.sequence,
        type=ChatFlagType.STARRED,
    )
    try:
        flags = await async_client.chat_flags.get_all(type=ChatFlagType.STARRED)
        request_ids = [f.source_request_id for f in flags]
        assert seeded_message.source_request_id in request_ids
    finally:
        with suppress(Exception):
            await async_client.chat_flags.remove(
                session_id=seeded_session.id,
                source_request_id=seeded_message.source_request_id,
                sequence=seeded_message.sequence,
                type=ChatFlagType.STARRED,
            )


async def test_chat_flag_remove(
    async_client: AsyncAlbert, seeded_session: ChatSession, seeded_message: ChatMessage
):
    """Test removing a flag leaves the message without that flag type."""
    await async_client.chat_flags.add(
        session_id=seeded_session.id,
        source_request_id=seeded_message.source_request_id,
        sequence=seeded_message.sequence,
        type=ChatFlagType.STARRED,
    )
    await async_client.chat_flags.remove(
        session_id=seeded_session.id,
        source_request_id=seeded_message.source_request_id,
        sequence=seeded_message.sequence,
        type=ChatFlagType.STARRED,
    )
    # TODO(backend): simplify to a plain get_by_message() assert once the backend
    # returns an empty list instead of 404 when no flags remain on a message.
    try:
        flags_in_message = await async_client.chat_flags.get_by_message(
            session_id=seeded_session.id,
            source_request_id=seeded_message.source_request_id,
            sequence=seeded_message.sequence,
        )
        assert ChatFlagType.STARRED not in (flags_in_message.flags or [])
    except NotFoundError:
        pass  # 404 = no flags remain; removal confirmed
