import pytest

from albert.client import Albert
from albert.resources.design_candidate_sets import DesignCandidateSet
from albert.resources.design_candidates import DesignCandidate
from albert.resources.design_runs import DesignRun, DesignRunState
from albert.resources.projects import Project

pytestmark = pytest.mark.xdist_group("projects")

ignore_in_ten0 = pytest.mark.xfail(
    reason="The v4 design service is not enabled for the TEN0 test tenant.",
    strict=False,
)


def _complete_run(client: Albert, parent_id: str) -> DesignRun:
    run = next(
        client.design_runs_v4.get_all(
            parent_id=parent_id, state=DesignRunState.COMPLETE, max_items=1
        ),
        None,
    )
    if run is None:
        pytest.skip("No completed design run in this tenant.")
    return run


@ignore_in_ten0
def test_get_run_and_rename_round_trip(client: Albert, seeded_projects: list[Project]) -> None:
    """Test reading a stored run and renaming it, then restoring the name."""
    run = _complete_run(client, seeded_projects[0].id)
    fetched = client.design_runs_v4.get_by_id(id=run.id)
    assert isinstance(fetched, DesignRun)
    assert fetched.state == DesignRunState.COMPLETE
    assert fetched.result_set_id is not None

    original = fetched.name
    try:
        fetched.name = f"{original} (renamed)"
        assert client.design_runs_v4.update(design_run=fetched).name == f"{original} (renamed)"
    finally:
        restored = client.design_runs_v4.get_by_id(id=run.id)
        restored.name = original
        client.design_runs_v4.update(design_run=restored)


@ignore_in_ten0
def test_get_candidate_set_and_candidates(client: Albert, seeded_projects: list[Project]) -> None:
    """Test reading a completed run's candidate set, its candidates, and one by id."""
    run = _complete_run(client, seeded_projects[0].id)

    candidate_set = client.design_candidate_sets.get_by_id(id=run.result_set_id)
    assert isinstance(candidate_set, DesignCandidateSet)
    assert candidate_set.source.source_id == run.id

    from_set = list(client.design_candidate_sets.get_candidates(id=candidate_set.id, max_items=5))
    listed = list(client.design_candidates.get_all(candidate_set_id=candidate_set.id, max_items=5))
    assert from_set
    assert [c.id for c in from_set] == [c.id for c in listed]
    assert all(isinstance(c, DesignCandidate) for c in listed)
    assert all(c.candidate_set_id == candidate_set.id for c in listed)

    fetched = client.design_candidates.get_by_id(id=listed[0].id)
    assert fetched.id == listed[0].id
    assert fetched.inputs
