from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import BaseResource


class ChatComponentType(str, Enum):
    """Component type of a chat message."""

    TEXT = "text"
    IMAGE = "image"
    REASONING_BLOCK = "reasoning_block"
    NOTEBOOK_CITATION = "notebook_citation"
    PRODUCT_CARD = "product_card"
    INGREDIENT_CARD = "ingredient_card"


class ChatUserType(str, Enum):
    """Origin of a chat message (user-submitted vs system-generated)."""

    USER = "user"
    SYSTEM = "system"


class ChatRole(str, Enum):
    """Chat role for a message, as used by the LLM conversation model."""

    USER = "user"
    ASSISTANT = "assistant"


class ChatFolderType(str, Enum):
    """Hierarchy level of a chat folder."""

    ROOT = "root"
    CHILD = "child"


class ChatSession(BaseResource):
    """
    A persistent chat session.

    Attributes
    ----------
    id : str | None
        The session ID assigned by the server.
    name : str
        The display name of the session.
    parent_id : str | None
        Optional folder ID that contains this session.
    source_session_id : str
        External session identifier for linking to a source system.
    last_message_at : str | None
        ISO 8601 timestamp of the most recent message in the session.
    """

    id: str | None = Field(default=None)
    name: str
    parent_id: str | None = Field(default=None, alias="parentId")
    source_session_id: str = Field(alias="sourceSessionId")
    last_message_at: str | None = Field(default=None, alias="lastMessageAt")


class ChatMessage(BaseResource):
    """
    A single message component within a chat session.

    Attributes
    ----------
    id : str | None
        The message ID assigned by the server.
    source_request_id : str | None
        Client-generated request trace identifier. Auto-generated on create if not set.
    sequence : str | None
        Zero-padded position of this message in the session (e.g. "000", "001").
    component_type : ChatComponentType
        The type of message component (e.g. text, image, reasoning_block).
    user_type : ChatUserType
        Whether the message originates from a user or the system.
    role : ChatRole
        The LLM conversation role (user or assistant).
    content : str | dict[str, Any]
        Component-type-specific payload; a string or free-form object.
    parent_id : str | None
        The session ID this message belongs to. Present in GET responses;
        derived from the URL path on create.
    component_id : str | None
        Component instance identifier.
    parent_request_id : str | None
        Parent request ID for branched messages.
    branch_index : int | None
        Branch index for branched messages.
    span_id : str | None
        Span/trace identifier.
    is_visible : bool | None
        Whether the component is visible in the UI.
    display_feedback_component : bool | None
        Whether to show the feedback UI for this message.
    """

    id: str | None = Field(default=None)
    source_request_id: str | None = Field(default=None, alias="sourceRequestId")
    sequence: str | None = Field(default=None)
    component_type: ChatComponentType = Field(alias="componentType")
    user_type: ChatUserType = Field(alias="userType")
    role: ChatRole = Field(alias="role")
    content: str | dict[str, Any] = Field(alias="Content")
    parent_id: str | None = Field(default=None, alias="parentId")
    component_id: str | None = Field(default=None, alias="componentId")
    parent_request_id: str | None = Field(default=None, alias="parentRequestId")
    branch_index: int | None = Field(default=None, alias="branchIndex")
    span_id: str | None = Field(default=None, alias="spanId")
    is_visible: bool | None = Field(default=None, alias="isVisible")
    display_feedback_component: bool | None = Field(default=None, alias="displayFeedbackComponent")
    value: list[dict] | None = Field(default=None)


class ChatFolder(BaseResource):
    """
    A folder used to organise chat sessions.

    Attributes
    ----------
    id : str | None
        The folder ID assigned by the server.
    name : str
        The display name of the folder.
    folder_type : ChatFolderType | None
        Whether this is a root or child folder.
    parent_id : str | None
        Optional parent folder ID for nested folders.
    """

    id: str | None = Field(default=None)
    name: str
    folder_type: ChatFolderType | None = Field(default=None, alias="type")
    parent_id: str | None = Field(default=None, alias="parentId")


class ChatFlagType(str, Enum):
    """Type of flag that can be applied to a chat message."""

    STARRED = "starred"
    DOWNLOADED = "downloaded"
    REQUESTED = "requested"
    HALLUCINATED = "hallucinated"


class ChatFlag(BaseResource):
    """
    A flag applied to a chat message.

    Attributes
    ----------
    source_request_id : str | None
        Request/trace identifier for the flagged message.
    id : str | None
        Message identifier.
    parent_id : str | None
        Parent session ID of the flagged message.
    type : ChatFlagType | None
        The type of flag.
    component_type : ChatComponentType | None
        Component type of the flagged message.
    sequence : str | None
        Zero-padded sequence of the flagged message.
    starred : bool | None
        Whether the message is starred.
    requested : bool | None
        Whether the message is marked as requested.
    downloaded : bool | None
        Whether the message is marked as downloaded.
    hallucinated : bool | None
        Whether the message is marked as hallucinated.
    """

    source_request_id: str | None = Field(default=None, alias="sourceRequestId")
    id: str | None = Field(default=None)
    parent_id: str | None = Field(default=None, alias="parentId")
    type: ChatFlagType | None = Field(default=None)
    component_type: ChatComponentType | None = Field(default=None, alias="componentType")
    sequence: str | None = Field(default=None)
    starred: bool | None = Field(default=None)
    requested: bool | None = Field(default=None)
    downloaded: bool | None = Field(default=None)
    hallucinated: bool | None = Field(default=None)


class ChatFlagsInMessage(BaseAlbertModel):
    """
    The set of flags applied to a specific chat message.

    Attributes
    ----------
    source_request_id : str | None
        Request/trace identifier for the message.
    total : int | None
        Total number of flags on the message.
    flags : list[ChatFlagType] | None
        List of flag types set on the message.
    """

    source_request_id: str | None = Field(default=None, alias="sourceRequestId")
    total: int | None = None
    flags: list[ChatFlagType] | None = None
