import inspect
import uuid

import pytest
from pydantic import ValidationError

from albert.collections.design_runs import DesignRunCollection
from albert.resources.chats import ChatSessionRef
from albert.resources.design import (
    DesignMethod,
    DOEDesignRunRequest,
    DOERunSettings,
    OptimizationDesignRunRequest,
    OptimizationRunSettings,
)
from albert.resources.targets import Criterion


def _wire(request: OptimizationDesignRunRequest | DOEDesignRunRequest) -> dict:
    return request.model_dump(by_alias=True, mode="json", exclude_none=True)


def test_optimization_request_has_method_discriminator() -> None:
    """Test OptimizationDesignRunRequest pins method generate."""
    request = OptimizationDesignRunRequest(smart_dataset_id="SDT1")
    assert request.method == DesignMethod.GENERATE


def test_doe_request_has_method_discriminator() -> None:
    """Test DOEDesignRunRequest pins method space_filling."""
    request = DOEDesignRunRequest(smart_dataset_id="SDT1")
    assert request.method == DesignMethod.SPACE_FILLING


def test_create_optimization_serializes_generate_method() -> None:
    """Test optimization request body uses method generate."""
    body = _wire(OptimizationDesignRunRequest(smart_dataset_id="SDT1"))
    assert body == {"smartDatasetId": "SDT1", "method": "generate"}


def test_create_doe_serializes_space_filling_method_and_settings() -> None:
    """Test DOE request body uses method space_filling and candidate settings keys."""
    settings = DOERunSettings(num_candidates_generated=5000, num_candidates_selected=5)
    body = _wire(DOEDesignRunRequest(smart_dataset_id="SDT2", settings=settings))
    assert body["method"] == "space_filling"
    assert body["settings"] == {
        "numCandidatesGenerated": 5000,
        "numCandidatesSelected": 5,
    }


def test_create_doe_serializes_anchor_targets_as_plain_list() -> None:
    """Test anchor_targets serializes to anchorTargets as a plain list."""
    body = _wire(
        DOEDesignRunRequest(
            smart_dataset_id="SDT3",
            anchor_targets=["TAR1", "TAR2"],
        )
    )
    assert body["anchorTargets"] == ["TAR1", "TAR2"]
    assert isinstance(body["anchorTargets"], list)


def test_create_optimization_serializes_objectives_and_settings() -> None:
    """Test optimization request serializes objectives and optimization settings."""
    objectives = {"TAR1": Criterion(operator="gte", value=1.0)}
    settings = OptimizationRunSettings(num_candidates_generated=1000, num_candidates_selected=10)
    body = _wire(
        OptimizationDesignRunRequest(
            smart_dataset_id="SDT4",
            objectives=objectives,
            settings=settings,
        )
    )
    assert body["method"] == "generate"
    assert body["objectives"] == {"TAR1": {"operator": "gte", "value": 1.0}}
    assert body["settings"] == {
        "numCandidatesGenerated": 1000,
        "numCandidatesSelected": 10,
    }


def test_create_optimization_with_chat_session_serializes_session_key() -> None:
    """Test create_optimization emits session when chat_session is provided."""
    session = ChatSessionRef(
        source_session_id=uuid.uuid4(),
        chat_session_id="SES-test",
    )
    body = _wire(
        OptimizationDesignRunRequest(
            smart_dataset_id="SDT5",
            session=session,
        )
    )
    assert body["session"] == {
        "sourceSessionId": str(session.source_session_id),
        "chatSessionId": "SES-test",
    }


def test_create_doe_with_chat_session_serializes_session_key() -> None:
    """Test create_doe emits session when chat_session is provided."""
    session = ChatSessionRef(
        source_session_id=uuid.uuid4(),
        chat_session_id="SES-doe",
    )
    body = _wire(DOEDesignRunRequest(smart_dataset_id="SDT6", session=session))
    assert body["session"] == {
        "sourceSessionId": str(session.source_session_id),
        "chatSessionId": "SES-doe",
    }


def test_validate_optimization_body_has_no_session_key() -> None:
    """Test validate request shape omits session unless provided."""
    session = ChatSessionRef(
        source_session_id=uuid.uuid4(),
        chat_session_id="SES-test",
    )
    body = _wire(OptimizationDesignRunRequest(smart_dataset_id="SDT7", session=session))
    assert "session" in body
    validate_body = _wire(OptimizationDesignRunRequest(smart_dataset_id="SDT7"))
    assert "session" not in validate_body


def test_validate_doe_body_has_no_session_key() -> None:
    """Test validate request shape omits session unless provided."""
    validate_body = _wire(DOEDesignRunRequest(smart_dataset_id="SDT8"))
    assert "session" not in validate_body


def test_create_optimization_rejects_objectives_keyword_on_create_doe() -> None:
    """Test create_doe has no objectives parameter."""
    sig = inspect.signature(DesignRunCollection.create_doe)
    assert "objectives" not in sig.parameters
    with pytest.raises(ValidationError, match="objectives"):
        DesignRunCollection.create_doe(  # type: ignore[call-arg]
            None,  # type: ignore[arg-type]
            smart_dataset_id="SDT1",
            objectives={"TAR1": Criterion(operator="gte", value=1.0)},
        )


def test_create_doe_rejects_anchor_targets_keyword_on_create_optimization() -> None:
    """Test create_optimization has no anchor_targets parameter."""
    sig = inspect.signature(DesignRunCollection.create_optimization)
    assert "anchor_targets" not in sig.parameters
    with pytest.raises(ValidationError, match="anchor_targets"):
        DesignRunCollection.create_optimization(  # type: ignore[call-arg]
            None,  # type: ignore[arg-type]
            smart_dataset_id="SDT1",
            anchor_targets=["TAR1"],
        )


def test_design_run_request_dump_includes_method() -> None:
    """Test wire dump emits method with tier-1 values."""
    assert _wire(OptimizationDesignRunRequest(smart_dataset_id="SDT1")) == {
        "smartDatasetId": "SDT1",
        "method": "generate",
    }
    assert _wire(DOEDesignRunRequest(smart_dataset_id="SDT2")) == {
        "smartDatasetId": "SDT2",
        "method": "space_filling",
    }


def test_optimization_run_settings_round_trip_camel_case() -> None:
    """Test OptimizationRunSettings round-trips with the expected camelCase keys."""
    settings = OptimizationRunSettings(num_candidates_generated=500, num_candidates_selected=15)
    dumped = settings.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped == {
        "numCandidatesGenerated": 500,
        "numCandidatesSelected": 15,
    }


def test_doe_run_settings_round_trip_camel_case() -> None:
    """Test DOERunSettings round-trips with the expected camelCase keys."""
    settings = DOERunSettings(
        num_candidates_generated=10_000,
        num_candidates_selected=10,
    )
    dumped = settings.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped == {
        "numCandidatesGenerated": 10_000,
        "numCandidatesSelected": 10,
    }
