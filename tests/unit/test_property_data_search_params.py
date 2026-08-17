"""Offline tests for property data search wire-parameter mapping."""

from unittest.mock import MagicMock

from albert.collections.property_data import PropertyDataCollection
from albert.core.shared.enums import OrderBy
from albert.core.shared.identifiers import LotId, UserId


def test_property_data_search_uses_api_wire_keys_for_lot_and_task_created_by() -> None:
    """Regression: API expects ``lot`` and ``taskCreatedby``, not ``lotIds`` / ``taskCreatedBy``."""
    session = MagicMock()
    collection = PropertyDataCollection(session=session)

    paginator = collection.search(
        lot_ids=[LotId("LOT1")],
        task_created_by=[UserId("USR1")],
        order=OrderBy.DESCENDING,
        max_items=1,
    )
    list(paginator)

    session.get.assert_called_once()
    _, kwargs = session.get.call_args
    params = kwargs["params"]
    assert "lot" in params
    assert params["lot"] == ["LOT1"]
    assert "lotIds" not in params
    assert "taskCreatedby" in params
    assert params["taskCreatedby"] == ["USR1"]
    assert "taskCreatedBy" not in params
