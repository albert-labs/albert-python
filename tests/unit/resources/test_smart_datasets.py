import pytest

from albert.resources.smart_datasets import SmartDatasetAggregateBy, SmartDatasetScope


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, None),
        (["WKS1", "WKS2"], ["WKS1", "WKS2"]),
        (["wks3"], ["WKS3"]),
        (["WKS1", "invalid", 123, None], ["WKS1"]),
        (["invalid", 42], None),
        ([], None),
    ],
)
def test_sheet_ids_filters_invalid_entries(raw, expected):
    """Test sheet_ids keeps only WKS-prefixed strings, coercing to None when none remain."""
    scope = SmartDatasetScope(sheet_ids=raw)
    assert scope.sheet_ids == expected


@pytest.mark.parametrize(
    "member, api_value",
    [
        (SmartDatasetAggregateBy.INV, "inventory"),
        (SmartDatasetAggregateBy.LOT, "lot"),
        (SmartDatasetAggregateBy.WFL, "workflow"),
        (SmartDatasetAggregateBy.PTD, "measurement"),
    ],
)
def test_aggregate_by_to_api_value(member, api_value):
    """Test SmartDatasetAggregateBy.to_api_value maps each member to its API string."""
    assert member.to_api_value() == api_value


@pytest.mark.parametrize(
    "api_value, member",
    [
        ("inventory", SmartDatasetAggregateBy.INV),
        ("lot", SmartDatasetAggregateBy.LOT),
        ("workflow", SmartDatasetAggregateBy.WFL),
        ("measurement", SmartDatasetAggregateBy.PTD),
    ],
)
def test_aggregate_by_from_api_value(api_value, member):
    """Test SmartDatasetAggregateBy.from_api_value maps each API string back to its member."""
    assert SmartDatasetAggregateBy.from_api_value(api_value) == member


def test_aggregate_by_from_api_value_rejects_unknown():
    """Test SmartDatasetAggregateBy.from_api_value raises for an unrecognized API value."""
    with pytest.raises(KeyError):
        SmartDatasetAggregateBy.from_api_value("unknown")
