from albert import Albert
from albert.resources.links import Link
from albert.resources.tasks import BaseTask


def test_link_get_all_basic(
    client: Albert, seeded_links: list[Link], seeded_tasks: list[BaseTask]
):
    """Test get all links with no filters."""
    results = list(client.links.get_all(max_items=10))
    task_ids = {t.id for t in seeded_tasks}

    for link in results:
        assert isinstance(link, Link)
        if link.child.id in task_ids:
            assert link.parent.id == seeded_tasks[0].id


def test_link_get_all_with_type_and_id(
    client: Albert, seeded_links: list[Link], seeded_tasks: list[BaseTask]
):
    """Test get_all with type='all' and specific task ID."""
    for task in seeded_tasks[1:]:
        results = list(client.links.get_all(id=task.id, type="all", max_items=10))
        for link in results:
            assert link.child.id == task.id
