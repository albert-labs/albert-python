from albert import Albert
from albert.resources.links import Link
from albert.resources.tasks import BaseTask


def test_list_links(seeded_links: list[Link], client: Albert, seeded_tasks: list[BaseTask]):
    for l in client.links.list():
        assert isinstance(l, Link)
        if l.child.id in [t.id for t in seeded_tasks]:  # If it was made in this test
            assert l.parent.id == seeded_tasks[0].id


def test_adv_list(seeded_links: list[Link], client: Albert, seeded_tasks: list[BaseTask]):
    for t in seeded_tasks[1:]:
        for l in client.links.list(id=t.id, type="all"):
            assert l.child.id == t.id
