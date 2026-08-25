import pytest

from albert import Albert
from albert.resources.workflows import Workflow

pytestmark = pytest.mark.xdist_group("tasks")


def test_workflow_get_all_with_pagination(client: Albert, seeded_workflows: list[Workflow]):
    fetched = client.workflows.get_by_ids(ids=[wf.id for wf in seeded_workflows[:10]])
    assert fetched, "Expected seeded workflows"
    for x in fetched:
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
