"""Unit tests for the stored design run resource model."""

from albert.resources.design_runs import DesignRun, DesignRunStage, DesignRunState


def test_a_run_keeps_a_state_and_stage_this_version_does_not_know():
    """Test that a newer state or stage reads as a string instead of failing a poll."""
    run = DesignRun.model_validate({"id": "DSR1", "state": "paused", "stage": "newStage"})

    assert run.state == "paused"
    assert run.stage == "newStage"


def test_a_run_parses_known_states_and_stages_to_the_enums():
    """Test that known values still parse to the enums."""
    run = DesignRun.model_validate(
        {"id": "DSR1", "state": "running", "stage": "generating_candidates"}
    )

    assert run.state is DesignRunState.RUNNING
    assert run.stage is DesignRunStage.GENERATING_CANDIDATES
