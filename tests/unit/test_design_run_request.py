import uuid

from albert.collections.design_runs import _build_design_run_request
from albert.resources.chats import ChatSessionRef


def test_build_request_includes_session_in_camel_case() -> None:
    source_id = uuid.uuid4()
    session = ChatSessionRef(source_session_id=source_id, chat_session_id="SES-test")
    body = _build_design_run_request(smart_dataset_id="SDT1", chat_session=session)
    assert body["session"] == {
        "sourceSessionId": str(source_id),
        "chatSessionId": "SES-test",
    }


def test_build_request_without_session_omits_key() -> None:
    body = _build_design_run_request(smart_dataset_id="SDT1")
    assert "session" not in body


def test_validate_path_body_never_contains_session() -> None:
    session = ChatSessionRef(
        source_session_id=uuid.uuid4(),
        chat_session_id="SES-test",
    )
    create_body = _build_design_run_request(smart_dataset_id="SDT1", chat_session=session)
    validate_body = _build_design_run_request(smart_dataset_id="SDT1")
    assert "session" in create_body
    assert "session" not in validate_body
