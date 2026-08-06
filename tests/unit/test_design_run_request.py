import uuid

from albert.collections.design_runs import _build_design_run_request


def test_build_request_includes_source_session_id_in_camel_case() -> None:
    source_id = uuid.uuid4()
    body = _build_design_run_request(smart_dataset_id="SDT1", source_session_id=source_id)
    assert body["sourceSessionId"] == str(source_id)


def test_build_request_without_session_omits_key() -> None:
    body = _build_design_run_request(smart_dataset_id="SDT1")
    assert "sourceSessionId" not in body


def test_build_request_carries_no_chat_session_id() -> None:
    """The SES id is derived by the platform, never sent by the SDK."""
    body = _build_design_run_request(smart_dataset_id="SDT1", source_session_id=uuid.uuid4())
    assert "chatSessionId" not in body
    assert "session" not in body


def test_validate_path_body_never_contains_session() -> None:
    create_body = _build_design_run_request(
        smart_dataset_id="SDT1", source_session_id=uuid.uuid4()
    )
    validate_body = _build_design_run_request(smart_dataset_id="SDT1")
    assert "sourceSessionId" in create_body
    assert "sourceSessionId" not in validate_body
