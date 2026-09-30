import pytest
from pydantic import ValidationError

from albert.resources.data_columns import DataColumn
from albert.resources.data_templates import CurveExample, DataColumnValue


def test_data_column_value_requires_data_column_or_id():
    """Test that DataColumnValue rejects construction with neither data_column nor data_column_id."""
    with pytest.raises(ValidationError, match="Either data_column_id or data_column must be set"):
        DataColumnValue(value="42")


def test_data_column_value_accepts_id_only():
    """Test that DataColumnValue accepts data_column_id alone."""
    value = DataColumnValue(data_column_id="DAC9999999", value="42")
    assert value.data_column_id == "DAC9999999"
    assert value.data_column is None


def test_data_column_value_derives_id_from_data_column():
    """Test that DataColumnValue fills data_column_id from data_column when only the latter is given."""
    column = DataColumn(id="DAC9999999", name="Viscosity")
    value = DataColumnValue(data_column=column)
    assert value.data_column_id == "DAC9999999"


def test_data_column_value_mismatched_ids_raises():
    """Test that DataColumnValue rejects data_column_id and data_column.id disagreeing."""
    column = DataColumn(id="DAC1111111", name="Viscosity")
    with pytest.raises(ValidationError, match="data_column_id and data_column.id must match"):
        DataColumnValue(data_column_id="DAC2222222", data_column=column)


def test_data_column_value_matching_ids_is_accepted():
    """Test that DataColumnValue accepts data_column_id matching data_column.id."""
    column = DataColumn(id="DAC1111111", name="Viscosity")
    value = DataColumnValue(data_column_id="DAC1111111", data_column=column)
    assert value.data_column_id == "DAC1111111"
    assert value.data_column is column


def test_curve_example_requires_exactly_one_source():
    """Test that CurveExample rejects having neither file_path nor attachment_id."""
    with pytest.raises(ValidationError, match="exactly one of file_path or attachment_id"):
        CurveExample()


def test_curve_example_rejects_both_sources():
    """Test that CurveExample rejects both file_path and attachment_id being set."""
    with pytest.raises(ValidationError, match="exactly one of file_path or attachment_id"):
        CurveExample(file_path="curve.csv", attachment_id="ATT123")


def test_curve_example_accepts_file_path_only():
    """Test that CurveExample accepts a file_path source alone."""
    example = CurveExample(file_path="curve.csv")
    assert example.file_path == "curve.csv"
    assert example.attachment_id is None


def test_curve_example_accepts_attachment_id_only():
    """Test that CurveExample accepts an attachment_id source alone."""
    example = CurveExample(attachment_id="ATT123")
    assert example.attachment_id == "ATT123"
    assert example.file_path is None
