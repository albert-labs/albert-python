import pytest

from albert import Albert
from albert.exceptions import NotFoundError
from albert.resources.workflows import Workflow, WorkflowSearchItem
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("tasks")

search_not_deployed = pytest.mark.xfail(
    reason="POST /api/v3/workflows/search is not yet deployed (api-workflow#129). Remove decorator once live.",
    raises=NotFoundError,
    strict=False,
)


def test_workflow_get_all_with_pagination(client: Albert, seeded_workflows: list[Workflow]):
    for x in list(client.workflows.get_all(max_items=10)):
        assert isinstance(x, Workflow)


def test_get_by_id(client: Albert, seeded_workflows: list[Workflow]):
    wf = seeded_workflows[0]
    retrieved_wf = client.workflows.get_by_id(id=wf.id)
    assert retrieved_wf.id == wf.id


def test_blocks_dupes(client: Albert, seeded_workflows: list[Workflow]):
    wf = seeded_workflows[0].model_copy()
    wf.id = None
    wf.status = None

    r = client.workflows.create(workflows=wf)
    assert r[0].id == seeded_workflows[0].id


@search_not_deployed
def test_workflow_search_basic(client: Albert, seeded_workflows: list[Workflow]):
    """Test search returns WorkflowSearchItem results with WFL ids."""
    results = list(client.workflows.search(max_items=10))
    assert results, "Expected at least one workflow search result"
    for item in results:
        assert isinstance(item, WorkflowSearchItem)
        assert item.id.startswith("WFL")
        assert item.name


@search_not_deployed
def test_workflow_search_by_text(
    client: Albert, seed_prefix: str, seeded_workflows: list[Workflow]
):
    """Test text search scoped to seed_prefix finds seeded workflows."""
    seeded_ids = {wf.id for wf in seeded_workflows}
    hits = poll_until(
        lambda: [
            item
            for item in client.workflows.search(text=seed_prefix, max_items=100)
            if item.id in seeded_ids
        ]
    )
    assert hits, "Expected at least one seeded workflow in text search results"


@search_not_deployed
def test_workflow_search_by_ids(client: Albert, seeded_workflows: list[Workflow]):
    """Test search by workflow ids returns seeded workflows."""
    seeded_ids = {wf.id for wf in seeded_workflows}
    hits = poll_until(
        lambda: [
            item
            for item in client.workflows.search(ids=[wf.id for wf in seeded_workflows])
            if item.id in seeded_ids
        ]
    )
    assert hits, "Expected at least one seeded workflow in id search results"
    assert {item.id for item in hits}.issubset(seeded_ids)


@search_not_deployed
def test_workflow_search_hydrate(
    client: Albert, seed_prefix: str, seeded_workflows: list[Workflow]
):
    """Test hydrating a search hit returns a full Workflow."""
    seeded_ids = {wf.id for wf in seeded_workflows}
    hits = poll_until(
        lambda: [
            item
            for item in client.workflows.search(text=seed_prefix, max_items=100)
            if item.id in seeded_ids
        ]
    )
    assert hits, "Expected at least one seeded workflow in search results"

    hydrated = hits[0].hydrate()
    assert isinstance(hydrated, Workflow)
    assert hydrated.id == hits[0].id
    assert hydrated.name == hits[0].name


@search_not_deployed
def test_workflow_search_by_parameter_groups(
    client: Albert,
    seed_prefix: str,
    seeded_workflows: list[Workflow],
    seeded_parameter_groups,
):
    """Test search by parameter group name scoped to seeded workflow ids."""
    seeded_ids = {wf.id for wf in seeded_workflows}
    group_name = seeded_parameter_groups[0].name
    hits = poll_until(
        lambda: [
            item
            for item in client.workflows.search(
                text=seed_prefix,
                parameter_groups=group_name,
                max_items=100,
            )
            if item.id in seeded_ids
        ]
    )
    assert hits, "Expected at least one seeded workflow matching parameter group filter"
