import inspect
import uuid

import pytest
from pydantic import ValidationError

from albert.collections.design_runs import (
    DesignRunCollection,
    _build_doe_run_request,
    _build_optimization_run_request,
)
from albert.resources.chats import ChatSessionRef
from albert.resources.design import DOERunSettings, OptimizationRunSettings
from albert.resources.targets import Criterion


def test_create_optimization_serializes_generate_method() -> None:
    """Test optimization request body uses method generate."""
    body = _build_optimization_run_request(smart_dataset_id="SDT1")
    assert body == {"smartDatasetId": "SDT1", "method": "generate"}


def test_create_doe_serializes_space_filling_method_and_settings() -> None:
    """Test DOE request body uses method space_filling and DOE settings keys."""
    settings = DOERunSettings(num_proposals=5, num_samples_per_dimension=10)
    body = _build_doe_run_request(smart_dataset_id="SDT2", settings=settings)
    assert body["method"] == "space_filling"
    assert body["settings"] == {
        "numProposals": 5,
        "numSamplesPerDimension": 10,
    }


def test_create_doe_serializes_anchor_targets_as_plain_list() -> None:
    """Test anchor_targets serializes to anchorTargets as a plain list."""
    body = _build_doe_run_request(
        smart_dataset_id="SDT3",
        anchor_targets=["TAR1", "TAR2"],
    )
    assert body["anchorTargets"] == ["TAR1", "TAR2"]
    assert isinstance(body["anchorTargets"], list)


def test_create_optimization_serializes_objectives_and_settings() -> None:
    """Test optimization request serializes objectives and optimization settings."""
    objectives = {"TAR1": Criterion(operator="gte", value=1.0)}
    settings = OptimizationRunSettings(num_candidates_generated=1000, num_candidates_selected=10)
    body = _build_optimization_run_request(
        smart_dataset_id="SDT4",
        objectives=objectives,
        settings=settings,
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
    body = _build_optimization_run_request(
        smart_dataset_id="SDT5",
        chat_session=session,
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
    body = _build_doe_run_request(
        smart_dataset_id="SDT6",
        chat_session=session,
    )
    assert body["session"] == {
        "sourceSessionId": str(session.source_session_id),
        "chatSessionId": "SES-doe",
    }


def test_validate_optimization_body_has_no_session_key() -> None:
    """Test validate_optimization builder never includes session."""
    session = ChatSessionRef(
        source_session_id=uuid.uuid4(),
        chat_session_id="SES-test",
    )
    body = _build_optimization_run_request(
        smart_dataset_id="SDT7",
        chat_session=session,
    )
    assert "session" in body
    validate_body = _build_optimization_run_request(smart_dataset_id="SDT7")
    assert "session" not in validate_body


def test_validate_doe_body_has_no_session_key() -> None:
    """Test validate_doe builder never includes session."""
    validate_body = _build_doe_run_request(smart_dataset_id="SDT8")
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
        num_proposals=10,
        max_num_polytopes=3,
        max_num_samples=100,
    )
    dumped = settings.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert dumped == {
        "numProposals": 10,
        "maxNumPolytopes": 3,
        "maxNumSamples": 100,
    }
