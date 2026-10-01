import pytest

from albert.resources.chats import (
    ChatComponentType,
    ChatMessage,
    ChatRole,
    ChatSession,
    ChatSessionKind,
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


def test_chat_message_permission_actions_wire_alias_round_trip():
    """Test permission_actions serializes to and parses from its camelCase wire alias."""
    permission_actions = [
        {
            "permissionId": "prm_one",
            "action": "allow_once",
            "permissionKey": "inventory.write",
        },
        {
            "permissionId": "prm_two",
            "action": "allow_always",
            "permissionKey": "projects.delete",
        },
    ]
    message = ChatMessage(
        component_type=ChatComponentType.TEXT,
        user_type=ChatUserType.USER,
        role=ChatRole.USER,
        content="Permission response.",
        permission_actions=permission_actions,
    )

    dumped = message.model_dump(by_alias=True, exclude_none=True)
    assert dumped["permissionActions"] == permission_actions

    restored = ChatMessage.model_validate(
        {
            "componentType": "text",
            "userType": "user",
            "role": "user",
            "Content": "Permission response.",
            "permissionActions": permission_actions,
        }
    )
    assert restored.permission_actions == permission_actions


def test_chat_message_omits_permission_actions_when_unset():
    """Test rows that answered no permission card carry neither permission field."""
    message = ChatMessage(
        component_type=ChatComponentType.TEXT,
        user_type=ChatUserType.USER,
        role=ChatRole.USER,
        content="Just a message.",
    )

    dumped = message.model_dump(by_alias=True, exclude_none=True)
    assert "permissionActions" not in dumped
    assert "permissionAction" not in dumped


def test_chat_message_accepts_both_permission_fields():
    """Test the legacy single action and the batch can ride the same row."""
    message = ChatMessage.model_validate(
        {
            "componentType": "text",
            "userType": "user",
            "role": "user",
            "Content": "Permission response.",
            "permissionAction": {"permissionId": "prm_one", "action": "allow_once"},
            "permissionActions": [{"permissionId": "prm_one", "action": "allow_once"}],
        }
    )

    assert message.permission_action == {"permissionId": "prm_one", "action": "allow_once"}
    assert message.permission_actions == [{"permissionId": "prm_one", "action": "allow_once"}]


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


def test_chat_session_automation_fields_wire_alias_round_trip():
    """Test kind, automation_id and automation_run_id serialize to and parse from their camelCase aliases."""
    session = ChatSession(
        name="Automation run",
        source_session_id="11111111-1111-4111-8111-111111111111",
        kind=ChatSessionKind.AUTOMATION,
        automation_id="AUT1",
        automation_run_id="RUN1",
    )

    dumped = session.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert dumped == {
        "name": "Automation run",
        "sourceSessionId": "11111111-1111-4111-8111-111111111111",
        "kind": "automation",
        "automationId": "AUT1",
        "automationRunId": "RUN1",
    }

    restored = ChatSession.model_validate(
        {
            "id": "SES1",
            "name": "Automation run",
            "sourceSessionId": "11111111-1111-4111-8111-111111111111",
            "kind": "automation",
            "automationId": "AUT1",
            "automationRunId": "RUN1",
        }
    )
    assert restored.kind is ChatSessionKind.AUTOMATION
    assert restored.automation_id == "AUT1"
    assert restored.automation_run_id == "RUN1"


def test_chat_session_omits_automation_fields_when_unset():
    """Test the create payload is unchanged for a regular chat session."""
    session = ChatSession(name="Plain chat", source_session_id="ext-123")

    dumped = session.model_dump(by_alias=True, exclude_unset=True, mode="json")
    assert dumped == {"name": "Plain chat", "sourceSessionId": "ext-123"}
    assert session.kind is None
    assert session.automation_id is None
    assert session.automation_run_id is None


def test_chat_session_parses_legacy_response_without_kind():
    """Test a session response that predates the kind field still validates."""
    restored = ChatSession.model_validate(
        {"id": "SES1", "name": "Legacy", "sourceSessionId": "ext-123", "status": "active"}
    )
    assert restored.kind is None
    assert restored.automation_id is None


@pytest.mark.parametrize("value", ["chat", "automation"])
def test_chat_session_parses_kind_values(value: str):
    """Test both wire values of kind map onto ChatSessionKind."""
    restored = ChatSession.model_validate({"name": "n", "sourceSessionId": "s", "kind": value})
    assert restored.kind == ChatSessionKind(value)


def test_chat_session_rejects_unknown_kind():
    """Test an unknown kind value fails validation instead of passing through."""
    with pytest.raises(ValueError):
        ChatSession.model_validate({"name": "n", "sourceSessionId": "s", "kind": "bogus"})
