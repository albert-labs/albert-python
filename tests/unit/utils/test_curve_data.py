"""Unit tests for curve data read helpers."""

from __future__ import annotations

import gzip
import json

import pandas as pd
import pytest
import responses

from albert.resources.data_templates import Axis, CSVMapping, CurveDataEntityLink
from albert.resources.property_data import (
    DataInterval,
    PropertyData,
    PropertyValue,
    TaskPropertyData,
    Trial,
)
from albert.utils.curve_data import (
    CURVE_REPORT_PATH,
    CURVE_ROW_LIMIT,
    build_curve_query_payload,
    curve_query_source,
    curve_rows_to_dataframe,
    fetch_curve_rows,
    find_task_curves,
    parse_curve_file,
    resolve_curve_columns,
)
from tests.unit.conftest import UNIT_BASE_URL

CURVE_LINKS = [
    CurveDataEntityLink(id="DAC2", name="param_B", axis=Axis.Y),
    CurveDataEntityLink(id="DAC1", name="param_A", axis=Axis.X),
]


def _curve_property_data(**overrides) -> PropertyData:
    data = {
        "id": "PTD1",
        "valueType": "curve",
        "value": "curve.csv",
        "s3Key": {"rawfile": "curve-input/raw.csv", "s3Input": "curve-input/input.csv"},
        "athena": {"tableName": "dat1_dac9", "partitionKey": "uuid-1"},
        "csvMapping": {"Temperature": "dac1", "Count": "dac2"},
    }
    data.update(overrides)
    return PropertyData.model_validate(data)


def _block(*, trials: list[Trial], interval_void: bool = False, block_id: str = "BLK1"):
    return TaskPropertyData(
        parent_id="TAS1",
        task_id="TAS1",
        block_id=block_id,
        data_template={"id": "DAT1"},
        data=[DataInterval(interval_combination="default", void=interval_void, trials=trials)],
    )


def _trial(*columns: PropertyValue, number: int = 1, void: bool = False) -> Trial:
    return Trial(trial_number=number, void=void, data_columns=list(columns))


def test_curve_query_source_prefers_s3_input():
    """Test the query source uses the table, partition key, and s3 input key."""
    assert curve_query_source(property_data=_curve_property_data()) == (
        "dat1_dac9",
        "uuid-1",
        "curve-input/input.csv",
    )


def test_curve_query_source_falls_back_to_rawfile():
    """Test the raw file key is used when there is no s3 input key."""
    property_data = _curve_property_data(s3Key={"rawfile": "curve-input/raw.csv"})
    assert curve_query_source(property_data=property_data)[2] == "curve-input/raw.csv"


@pytest.mark.parametrize(
    "overrides",
    [
        {"valueType": "string"},
        {"athena": None},
        {"athena": {"tableName": "dat1_dac9"}},
        {"s3Key": None},
        {"s3Key": {"preview": "p.webp"}},
    ],
)
def test_curve_query_source_none_when_not_readable(overrides):
    """Test values that are not stored curves have no query source."""
    assert curve_query_source(property_data=_curve_property_data(**overrides)) is None


def test_curve_query_source_none_without_property_data():
    """Test a column with no recorded value has no query source."""
    assert curve_query_source(property_data=None) is None


def test_find_task_curves_skips_non_curve_and_void():
    """Test only stored curves in non-void trials and intervals are returned."""
    curve = PropertyValue(id="DAC9", property_data=_curve_property_data())
    scalar = PropertyValue(id="DAC5", property_data=PropertyData(value="1", value_type="numeric"))
    empty = PropertyValue(id="DAC8")
    live = _block(trials=[_trial(curve, scalar, empty), _trial(curve, number=2, void=True)])
    voided = _block(trials=[_trial(curve)], interval_void=True, block_id="BLK2")

    found = find_task_curves(blocks=[live, voided])

    assert [(b.block_id, t.trial_number, c.id) for b, _, t, c in found] == [("BLK1", 1, "DAC9")]


def test_find_task_curves_include_void():
    """Test voided curves are returned when requested."""
    curve = PropertyValue(id="DAC9", property_data=_curve_property_data())
    block = _block(trials=[_trial(curve), _trial(curve, number=2, void=True)])

    found = find_task_curves(blocks=[block], include_void=True)

    assert [t.trial_number for _, _, t, _ in found] == [1, 2]


def test_find_task_curves_filters_block_and_column():
    """Test block and data column filters narrow the curves returned."""
    curve_a = PropertyValue(id="DAC9", property_data=_curve_property_data())
    curve_b = PropertyValue(id="DAC7", property_data=_curve_property_data())
    blocks = [
        _block(trials=[_trial(curve_a, curve_b)]),
        _block(trials=[_trial(curve_a)], block_id="BLK2"),
    ]

    found = find_task_curves(blocks=blocks, block_id="BLK1", data_column_id="DAC7")

    assert [(b.block_id, c.id) for b, _, _, c in found] == [("BLK1", "DAC7")]


def test_resolve_curve_columns_uses_csv_headers_with_x_first():
    """Test CSV headers name the columns and the X axis column comes first."""
    columns = resolve_curve_columns(
        csv_mapping={"Count": "dac2", "Temperature": "dac1"}, curve_data=CURVE_LINKS
    )
    assert list(columns.items()) == [("DAC1", "Temperature"), ("DAC2", "Count")]


def test_resolve_curve_columns_accepts_csv_mapping_model():
    """Test a CSVMapping model is read through its mapping data."""
    columns = resolve_curve_columns(
        csv_mapping=CSVMapping(map_data={"Temperature": "dac1"}), curve_data=None
    )
    assert columns == {"DAC1": "Temperature"}


def test_resolve_curve_columns_falls_back_to_curve_links():
    """Test curve result names are used when there is no CSV mapping."""
    columns = resolve_curve_columns(csv_mapping=None, curve_data=CURVE_LINKS)
    assert list(columns.items()) == [("DAC1", "param_A"), ("DAC2", "param_B")]


def test_build_curve_query_payload_for_task():
    """Test a task curve query filters by task, block, template, and partition."""
    payload = build_curve_query_payload(
        data_template_id="DAT1",
        table_name="dat1_dac9",
        partition_key="uuid-1",
        file_key="curve-input/input.csv",
        column_ids=["DAC1", "dac2"],
        source_id="TAS1",
        parent_id="TAS1",
        block_id="BLK1",
    )
    assert payload == {
        "dataTemplate": {"id": "DAT1"},
        "tableName": "dat1_dac9",
        "filters": [
            {"type": "filter", "id": "parentid", "op": "=", "value": "TAS1"},
            {"type": "filter", "id": "blockid", "op": "=", "value": "BLK1"},
            {"type": "filter", "id": "datatemplateid", "op": "=", "value": "DAT1"},
            {"type": "filter", "id": "uuid", "op": "=", "value": "uuid-1"},
        ],
        "select": [{"type": "DAC", "id": "DAC1"}, {"type": "DAC", "id": "DAC2"}],
        "limit": CURVE_ROW_LIMIT,
        "offset": 0,
        "fileKey": "curve-input/input.csv",
        "source": "TAS1",
    }


def test_build_curve_query_payload_for_template_example():
    """Test a template example query uses null parent and block filters."""
    payload = build_curve_query_payload(
        data_template_id="DAT1",
        table_name="dat1_dac9",
        partition_key="uuid-1",
        file_key="curve-input/input.csv",
        column_ids=["DAC1"],
        source_id="DAT1",
    )
    assert payload["filters"][:2] == [
        {"type": "filter", "id": "parentid", "op": "=", "value": "null"},
        {"type": "filter", "id": "blockid", "op": "=", "value": "null"},
    ]
    assert payload["source"] == "DAT1"


def test_parse_curve_file_reads_gzipped_json_lines():
    """Test a gzipped JSON Lines file is decoded into rows, skipping blank lines."""
    content = gzip.compress(b'{"dac1":"0","dac2":"6"}\n\n{"dac1":"10","dac2":"11"}\n')
    assert parse_curve_file(content=content) == [
        {"dac1": "0", "dac2": "6"},
        {"dac1": "10", "dac2": "11"},
    ]


def test_curve_rows_to_dataframe_renames_and_sorts_without_coercing():
    """Test rows are renamed to display names and ordered by X, keeping values as stored."""
    rows = [
        {"dac1": "23", "dac2": "24"},
        {"DAC1": "hello", "DAC2": "5"},
        {"dac1": "0", "dac2": "6"},
    ]
    df = curve_rows_to_dataframe(
        rows=rows, columns={"DAC1": "Temperature", "DAC2": "Count"}, sort_by="Temperature"
    )
    expected = pd.DataFrame({"Temperature": ["0", "23", "hello"], "Count": ["6", "24", "5"]})
    pd.testing.assert_frame_equal(df, expected)


def test_curve_rows_to_dataframe_empty_keeps_columns():
    """Test an empty curve still has its named columns."""
    df = curve_rows_to_dataframe(rows=[], columns={"DAC1": "Temperature"}, sort_by="Temperature")
    assert df.empty
    assert list(df.columns) == ["Temperature"]


@responses.activate
def test_fetch_curve_rows_inline_items(offline_session):
    """Test inline rows are returned as they are."""
    responses.post(
        f"{UNIT_BASE_URL}{CURVE_REPORT_PATH}",
        json={"total": 1, "items": [{"DAC1": "0"}]},
    )
    assert fetch_curve_rows(session=offline_session, payload={}) == [{"DAC1": "0"}]


@responses.activate
def test_fetch_curve_rows_downloads_every_file_without_auth(offline_session):
    """Test result files are downloaded in order without sending the Albert token."""
    urls = ["https://files.example/part1.gz", "https://files.example/part2.gz"]
    responses.post(
        f"{UNIT_BASE_URL}{CURVE_REPORT_PATH}",
        json={"total": 2, "urls": [{"key": u, "url": u} for u in urls]},
    )
    for i, url in enumerate(urls):
        responses.get(url, body=gzip.compress(json.dumps({"dac1": str(i)}).encode()))

    rows = fetch_curve_rows(session=offline_session, payload={"tableName": "t"})

    assert rows == [{"dac1": "0"}, {"dac1": "1"}]
    assert json.loads(responses.calls[0].request.body) == {"tableName": "t"}
    assert all("Authorization" not in call.request.headers for call in responses.calls[1:])
