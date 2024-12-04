from albert import Albert
from albert.resources.tasks import BaseTask


def test_task_list(client: Albert, seeded_tasks):
    tasks = client.tasks.list()
    for task in tasks:
        assert isinstance(task, BaseTask)


def test_get_by_id(client: Albert, seeded_tasks):
    task = client.tasks.get_by_id(id=seeded_tasks[0].id)
    assert isinstance(task, BaseTask)
    assert task.id == seeded_tasks[0].id
    assert task.name == seeded_tasks[0].name
