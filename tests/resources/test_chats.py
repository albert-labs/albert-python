from albert.resources.chats import (
    ChatComponentType,
    ChatMessage,
    ChatRole,
    ChatUserType,
)


def test_chat_message_serializes_page_context_to_page_context_alias() -> None:
    page_context = {
        "url": "https://app.albertinvent.com/#notebook",
        "entity": "notebook",
        "albert_id": "NTB1",
    }
    message = ChatMessage(
        component_type=ChatComponentType.TEXT,
        user_type=ChatUserType.USER,
        role=ChatRole.USER,
        content="hello",
        parent_id="SES-test",
        page_context=page_context,
    )

    dumped = message.model_dump(by_alias=True, mode="json")
    assert dumped["pageContext"] == page_context

    restored = ChatMessage.model_validate(dumped)
    assert restored.page_context == page_context
