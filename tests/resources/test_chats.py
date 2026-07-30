from albert.resources.chats import (
    ChatComponentType,
    ChatMessage,
    ChatRole,
    ChatUserType,
)


def test_chat_message_page_context_wire_alias_round_trip():
    """Test page_context serializes to and parses from its camelCase wire alias."""
    page_context = {
        "url": "https://example.com/#notebook",
        "entity": "notebook",
        "albert_id": "NTB1",
    }
    message = ChatMessage(
        component_type=ChatComponentType.TEXT,
        user_type=ChatUserType.USER,
        role=ChatRole.USER,
        content="hello",
        page_context=page_context,
    )

    dumped = message.model_dump(by_alias=True, exclude_none=True)
    assert dumped["pageContext"] == page_context

    restored = ChatMessage.model_validate(
        {
            "componentType": "text",
            "userType": "user",
            "role": "user",
            "Content": "hello",
            "pageContext": page_context,
        }
    )
    assert restored.page_context == page_context


def test_chat_message_omits_page_context_when_unset():
    """Test page_context is excluded from the payload when not provided."""
    message = ChatMessage(
        component_type=ChatComponentType.TEXT,
        user_type=ChatUserType.USER,
        role=ChatRole.USER,
        content="hello",
    )

    assert "pageContext" not in message.model_dump(by_alias=True, exclude_none=True)
    assert message.page_context is None


def test_chat_message_permission_action_wire_alias_round_trip():
    """Test permission_action serializes to and parses from its camelCase wire alias."""
    permission_action = {
        "permissionId": "prm_test",
        "action": "allow_session",
        "comment": "Allowed for this session",
    }
    message = ChatMessage(
        component_type=ChatComponentType.TEXT,
        user_type=ChatUserType.USER,
        role=ChatRole.USER,
        content="Allowed for this session.",
        permission_action=permission_action,
    )

    dumped = message.model_dump(by_alias=True, exclude_none=True)
    assert dumped["permissionAction"] == permission_action

    restored = ChatMessage.model_validate(
        {
            "componentType": "text",
            "userType": "user",
            "role": "user",
            "Content": "Allowed for this session.",
            "permissionAction": permission_action,
        }
    )
    assert restored.permission_action == permission_action


def test_chat_message_parses_permission_request_component_type():
    """Test the permission_request component type parses to its enum member."""
    restored = ChatMessage.model_validate(
        {
            "componentType": "permission_request",
            "userType": "system",
            "role": "assistant",
            "Content": {
                "permission_id": "prm_test",
                "status": "pending",
                "operation": "project_create",
            },
        }
    )
    assert restored.component_type is ChatComponentType.PERMISSION_REQUEST
