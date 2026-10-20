"""Unit tests for report resource model parsing."""

from albert.resources.reports import FullAnalyticalReport


def test_full_report_parses_null_grouped_row_entries():
    """Test that a saved metadata state with null grouped row entries parses and round-trips."""
    report = FullAnalyticalReport.model_validate(
        {
            "reportTypeId": "RET1",
            "name": "Report",
            "metaDataState": {"groupedRows": ["ROW1", None]},
        }
    )

    assert report.meta_data_state.grouped_rows == ["ROW1", None]
    dumped = report.model_dump(by_alias=True, mode="json")
    assert dumped["metaDataState"] == {"groupedRows": ["ROW1", None]}
