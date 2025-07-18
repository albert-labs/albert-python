from albert import Albert
from albert.resources.workflows import Workflow


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
