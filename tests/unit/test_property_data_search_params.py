"""Unit tests for property data search query-parameter wire keys."""

from unittest.mock import MagicMock

from albert.collections.property_data import PropertyDataCollection
from albert.core.shared.enums import OrderBy


def _search_params(**kwargs):
    session = MagicMock()
    paginator = PropertyDataCollection(session=session).search(**kwargs)
    return paginator.params


def test_property_data_search_lot_wire_key() -> None:
    """Test lot_ids maps to wire key lot, not lotIds."""
    params = _search_params(lot_ids=["LOT123"])
    assert params["lot"] == ["LOT123"]
    assert "lotIds" not in params


def test_property_data_search_task_created_by_wire_key() -> None:
    """Test task_created_by maps to wire key taskCreatedby."""
    params = _search_params(task_created_by="USR4227")
    assert params["taskCreatedby"] == ["USR4227"]
    assert "taskCreatedBy" not in params


def test_property_data_search_new_filters_wire_keys() -> None:
    """Test newly exposed search filters use API wire keys."""
    params = _search_params(
        order_by=OrderBy.ASCENDING,
        facet_list=["dataTemplates"],
        parameter_set=["viscosity@25C"],
        search_field=["dataColumns"],
        source_field=["inventoryId"],
        sheet_ids=["SHT1"],
    )
    assert params["orderBy"] == OrderBy.ASCENDING
    assert params["facetList"] == ["dataTemplates"]
    assert params["parameterSet"] == ["viscosity@25C"]
    assert params["searchField"] == ["dataColumns"]
    assert params["sourceField"] == ["inventoryId"]
    assert params["sheetIds"] == ["SHT1"]


def test_property_data_search_legacy_return_params_not_sent() -> None:
    """Test return_fields and return_facets are not sent to the API."""
    params = _search_params(return_fields=["inventoryId"], return_facets=["unit"])
    assert "returnFields" not in params
    assert "returnFacets" not in params
