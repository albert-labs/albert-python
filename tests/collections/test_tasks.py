from albert import Albert
from albert.resources.lists import ListItem
from albert.resources.tasks import BaseTask, PropertyTask
from tests.utils.test_patches import change_metadata, make_metadata_update_assertions


def test_task_list(client: Albert, seeded_tasks):
    tasks = client.tasks.list()
    for task in tasks:
        assert isinstance(task, BaseTask)


def test_get_by_id(client: Albert, seeded_tasks):
    task = client.tasks.get_by_id(id=seeded_tasks[0].id)
    assert isinstance(task, BaseTask)
    assert task.id == seeded_tasks[0].id
    assert task.name == seeded_tasks[0].name


def test_update(client: Albert, seeded_tasks, seed_prefix: str, static_lists: list[ListItem]):
    task = [x for x in seeded_tasks if "metadata" in x.name.lower()][0]
    new_name = f"{seed_prefix}-new name"
    task.name = new_name
    new_metadata = change_metadata(
        task.metadata, static_lists=static_lists, seed_prefix=seed_prefix
    )
    task.metadata = new_metadata
    updated_task = client.tasks.update(task=task)
    assert updated_task.name == new_name
    assert updated_task.id == task.id
    # check metadata updates
    make_metadata_update_assertions(new_metadata=new_metadata, updated_object=updated_task)


def test_add_block(client: Albert, seeded_tasks, seeded_workflows, seeded_data_templates):
    task = [x for x in seeded_tasks if isinstance(x, PropertyTask)][0]
    starting_blocks = len(task.blocks)
    client.tasks.add_block(
        task_id=task.id,
        data_template_id=seeded_data_templates[0].id,
        workflow_id=seeded_workflows[0].id,
    )
    updated_task = client.tasks.get_by_id(id=task.id)
    assert len(updated_task.blocks) == starting_blocks + 1


def test_update_block_workflow(
    client: Albert, seeded_tasks, seeded_workflows, seeded_data_templates
):
    task = [x for x in seeded_tasks if isinstance(x, PropertyTask)][0]
    # in case it mutated
    task = client.tasks.get_by_id(id=task.id)
    starting_blocks = len(task.blocks)
    block_id = task.blocks[0].id
    new_workflow = [x for x in seeded_workflows if x.id != task.blocks[0].workflow][0]
    client.tasks.update_block_workflow(
        task_id=task.id, block_id=block_id, workflow_id=new_workflow.id
    )
    updated_task = client.tasks.get_by_id(id=task.id)
    assert len(updated_task.blocks) == starting_blocks
    updated_block = [x for x in updated_task.blocks if x.id == block_id][0]
    assert new_workflow.id in [x.id for x in updated_block.workflow]


def test_task_get_history(client: Albert, seeded_tasks):
    task_history = client.tasks.get_history(id=seeded_tasks[0].id)
    assert isinstance(task_history.items, list)
