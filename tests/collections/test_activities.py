from datetime import date, timedelta

from albert import Albert
from albert.resources.activities import Activity, ActivityType


def assert_valid_activity_items(returned_list):
    assert returned_list, "Expected at least one activities result"
    for a in returned_list:
        assert isinstance(a, Activity)
        assert isinstance(a.id, str)


def test_activity_get_all(client: Albert):
    end_date = date.today()
    start_date = end_date - timedelta(days=1)
    simple_list = client.activities.get_all(
        type=ActivityType.DATE_RANGE,
        start_date=start_date,
        end_date=end_date,
        max_items=10,
    )
    assert_valid_activity_items(simple_list)
