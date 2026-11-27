"""Helpers for reading stored curve data back as DataFrames."""

from __future__ import annotations

import gzip
import json

import pandas as pd
import requests

from albert.core.logging import logger
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import DataTemplateId
from albert.resources.data_templates import (
    Axis,
    CSVMapping,
    CurveDataEntityLink,
    StorageKeyReference,
)
from albert.resources.property_data import (
    DataInterval,
    PropertyData,
    PropertyValue,
    TaskPropertyData,
    Trial,
)

CURVE_REPORT_PATH = "/api/v3/reports/curve"
CURVE_ROW_LIMIT = 150000
_DOWNLOAD_TIMEOUT_SECONDS = 120


def find_task_curves(
    *,
    blocks: list[TaskPropertyData],
    block_id: str | None = None,
    data_column_id: str | None = None,
    include_void: bool = False,
) -> list[tuple[TaskPropertyData, DataInterval, Trial, PropertyValue]]:
    """Return every stored curve in the given task blocks, matching the filters.

    A curve is stored when the data column's property data has a curve value with the
    query metadata (table, partition key, and source file) needed to read it back.
    """
    found = []
    for block in blocks:
        if block_id is not None and block.block_id != block_id:
            continue
        if block.data_template is None:
            continue
        for interval in block.data:
            for trial in interval.trials:
                if (interval.void or trial.void) and not include_void:
                    continue
                for column in trial.data_columns:
                    if data_column_id is not None and column.id != data_column_id:
                        continue
                    if curve_query_source(property_data=column.property_data) is None:
                        continue
                    found.append((block, interval, trial, column))
    return found


def curve_query_source(*, property_data: PropertyData | None) -> tuple[str, str, str] | None:
    """Return ``(table_name, partition_key, file_key)`` for a stored curve, else None."""
    if property_data is None or property_data.value_type != "curve":
        return None
    athena = property_data.athena or {}
    storage_key = property_data.storage_key
    file_key = None
    if isinstance(storage_key, StorageKeyReference):
        file_key = storage_key.s3_input or storage_key.rawfile
    table_name = athena.get("tableName")
    partition_key = athena.get("partitionKey")
    if not (table_name and partition_key and file_key):
        return None
    return table_name, partition_key, file_key


def resolve_curve_columns(
    *,
    csv_mapping: dict[str, str] | CSVMapping | None,
    curve_data: list[CurveDataEntityLink] | None,
) -> dict[str, str]:
    """Map each curve result column ID (upper case) to its display name.

    Names come from the CSV header mapping when present, falling back to the curve
    result column names on the data template. The X axis column is placed first.
    """
    if isinstance(csv_mapping, CSVMapping):
        csv_mapping = csv_mapping.map_data
    links = curve_data or []
    columns = {link.id.upper(): link.name or link.id.upper() for link in links}
    if csv_mapping:
        columns = {dac_id.upper(): header for header, dac_id in csv_mapping.items()}
    x_ids = [link.id.upper() for link in links if link.axis == Axis.X]
    return dict(sorted(columns.items(), key=lambda item: item[0] not in x_ids))


def x_axis_column_name(
    *, columns: dict[str, str], curve_data: list[CurveDataEntityLink] | None
) -> str | None:
    """Return the display name of the X axis column, if the curve defines one."""
    for link in curve_data or []:
        if link.axis == Axis.X and link.id.upper() in columns:
            return columns[link.id.upper()]
    return None


def build_curve_query_payload(
    *,
    data_template_id: DataTemplateId,
    table_name: str,
    partition_key: str,
    file_key: str,
    column_ids: list[str],
    source_id: str,
    parent_id: str | None = None,
    block_id: str | None = None,
) -> dict:
    """Build the curve query for one stored curve.

    Data template examples have no parent or block; they are stored under the literal
    ``"null"`` value.
    """
    filters = {
        "parentid": parent_id or "null",
        "blockid": block_id or "null",
        "datatemplateid": data_template_id,
        "uuid": partition_key,
    }
    return {
        "dataTemplate": {"id": data_template_id},
        "tableName": table_name,
        "filters": [
            {"type": "filter", "id": key, "op": "=", "value": value}
            for key, value in filters.items()
        ],
        "select": [{"type": "DAC", "id": column_id.upper()} for column_id in column_ids],
        "limit": CURVE_ROW_LIMIT,
        "offset": 0,
        "fileKey": file_key,
        "source": source_id,
    }


def parse_curve_file(*, content: bytes) -> list[dict]:
    """Decode a gzipped JSON Lines curve result file into rows."""
    text = gzip.decompress(content).decode("utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def curve_rows_to_dataframe(
    *, rows: list[dict], columns: dict[str, str], sort_by: str | None = None
) -> pd.DataFrame:
    """Build a DataFrame from curve rows, renaming column IDs to display names.

    Values are kept exactly as returned. When ``sort_by`` is given, rows are ordered by
    that column's numeric value (non-numeric values last) without changing the values.
    """
    renamed = [
        {columns.get(key.upper(), key): value for key, value in row.items()} for row in rows
    ]
    df = pd.DataFrame(renamed, columns=list(columns.values()))
    if sort_by is not None and not df.empty:
        df = df.sort_values(
            by=sort_by,
            key=lambda s: pd.to_numeric(s, errors="coerce"),
            kind="stable",
            na_position="last",
        ).reset_index(drop=True)
    return df


def fetch_curve_rows(*, session: AlbertSession, payload: dict) -> list[dict]:
    """Run a curve query and return every row, downloading result files when needed."""
    body = session.post(CURVE_REPORT_PATH, json=payload).json()
    if "urls" in body:
        rows = []
        for entry in body["urls"]:
            response = requests.get(entry["url"], timeout=_DOWNLOAD_TIMEOUT_SECONDS)
            response.raise_for_status()
            rows.extend(parse_curve_file(content=response.content))
    else:
        rows = body.get("items") or []
    if len(rows) >= CURVE_ROW_LIMIT:
        logger.warning(
            f"Curve data reached the {CURVE_ROW_LIMIT} row limit; results may be truncated."
        )
    return rows


def fetch_curve_dataframe(
    *,
    session: AlbertSession,
    data_template_id: DataTemplateId,
    table_name: str,
    partition_key: str,
    file_key: str,
    csv_mapping: dict[str, str] | CSVMapping | None,
    curve_data: list[CurveDataEntityLink] | None,
    source_id: str,
    parent_id: str | None = None,
    block_id: str | None = None,
) -> pd.DataFrame:
    """Read one stored curve into a DataFrame named by its display column names."""
    columns = resolve_curve_columns(csv_mapping=csv_mapping, curve_data=curve_data)
    if not columns:
        raise ValueError(
            f"Curve data in table '{table_name}' has no curve result columns to read."
        )
    payload = build_curve_query_payload(
        data_template_id=data_template_id,
        table_name=table_name,
        partition_key=partition_key,
        file_key=file_key,
        column_ids=list(columns),
        source_id=source_id,
        parent_id=parent_id,
        block_id=block_id,
    )
    rows = fetch_curve_rows(session=session, payload=payload)
    return curve_rows_to_dataframe(
        rows=rows,
        columns=columns,
        sort_by=x_axis_column_name(columns=columns, curve_data=curve_data),
    )
