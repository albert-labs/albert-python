from datetime import date, timedelta

from albert.albert import Albert
from albert.resources.activities import Activity, ActivityType


def _get_all_asserts(returned_list):
    found = False
    for i, a in enumerate(returned_list):
        if i == 30:
            break
        assert isinstance(a, Activity)
        assert isinstance(a.id, str)
        found = True
    assert found


def test_activity_get_all(client: Albert):
    end_date = date.today()
    start_date = end_date - timedelta(days=1)
    simple_list = client.activities.get_all(
        type=ActivityType.DATE_RANGE,
        start_date=start_date,
        end_date=end_date,
        limit=None,
    )
    _get_all_asserts(simple_list)
