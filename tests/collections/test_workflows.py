import copy

from albert import Albert
from albert.resources.workflows import Workflow


def test_basic_list(client: Albert, seeded_workflows: list[Workflow]):
    for wf in client.workflows.list():
        assert isinstance(wf, Workflow)


def test_get_by_id(client: Albert, seeded_workflows: list[Workflow]):
    wf = seeded_workflows[0]
    retrieved_wf = client.workflows.get_by_id(id=wf.id)
    assert retrieved_wf.id == wf.id


def test_blocks_dupes(client: Albert, seeded_workflows: list[Workflow]):
    wf = copy.deepcopy(seeded_workflows[0])
    wf.id = None
    wf.status = None

    r = client.workflows.create(workflow=wf)
    assert r.id == seeded_workflows[0].id
