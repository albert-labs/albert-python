import uuid
from contextlib import suppress
from datetime import date, timedelta

from albert import Albert
from albert.exceptions import NotFoundError
from albert.resources.activities import Activity, ActivitySearchItem, ActivityType
from albert.resources.tags import Tag
from tests.utils.wait import poll_until


def assert_valid_activity_items(returned_list):
    assert returned_list, "Expected at least one activities result"
    for a in returned_list:
        assert isinstance(a, Activity)
        assert isinstance(a.id, str)


def test_activity_get_all(client: Albert):
    """Test activity get_all returns the feed for a single entity."""
    tag = client.tags.create(tag=Tag(tag=f"TEST - activity scope {uuid.uuid4()}"))
    try:
        results = poll_until(
            lambda: list(
                client.activities.get_all(
                    type=ActivityType.ENTITY_ID,
                    id=tag.id,
                    max_items=10,
                )
            )
        )
        assert_valid_activity_items(results)
    finally:
        with suppress(NotFoundError):
            client.tags.delete(id=tag.id)


def test_activity_search(client: Albert):
    """Test that activity search returns ActivitySearchItem results."""
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    results = list(
        client.activities.search(
            start_date=start_date,
            end_date=end_date,
            max_items=10,
        )
    )
    assert results, "Expected at least one search result"
    for item in results:
        assert isinstance(item, ActivitySearchItem)
