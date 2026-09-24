from __future__ import annotations

from albert.resources.sheets import CellType, Sheet
from albert.resources.worksheets import Worksheet


def get_sheet_from_worksheet(*, sheet_name: str, worksheet: Worksheet) -> Sheet:
    sheet = next((s for s in worksheet.sheets if s.name == sheet_name), None)
    if not sheet:
        raise ValueError(f"Sheet with name {sheet_name!r} not found in the Worksheet.")
    return sheet


def get_columns_to_copy(
    *,
    sheet: Sheet,
    copy_all_pinned_columns: bool,
    copy_all_unpinned_columns: bool,
    input_column_names: list[str] | None,
) -> list[str]:
    sheet_columns = sheet.columns
    all_columns = {col.name: col.column_id for col in sheet_columns}

    # If both flags are true, copy everything
    if copy_all_pinned_columns and copy_all_unpinned_columns:
        columns_to_copy: set[str] = {col.column_id for col in sheet_columns}
    else:
        columns_to_copy = set()
        # Copy pinned columns
        if copy_all_pinned_columns:
            columns_to_copy.update(
                col.column_id for col in sheet_columns if getattr(col, "pinned", False)
            )

        # Copy unpinned columns
        if copy_all_unpinned_columns:
            columns_to_copy.update(
                col.column_id for col in sheet_columns if not getattr(col, "pinned", False)
            )

    # Add any explicitly specified columns
    if input_column_names:
        for name in input_column_names:
            if name not in all_columns:
                raise ValueError(f"Column name {name!r} not found in sheet {sheet.name!r}")
            columns_to_copy.add(all_columns[name])

    return list(columns_to_copy)


def get_task_rows_to_copy(*, sheet: Sheet, input_row_names: list[str] | None) -> list[str]:
    task_rows = []

    sheet_rows = sheet.rows
    if not input_row_names:
        # Copy all task rows if no input rows specified
        for row in sheet_rows:
            if row.type == CellType.TAS:
                task_rows.append(row.row_id)
        return task_rows

    name_to_id = {row.name: row.row_id for row in sheet_rows if row.name}
    for name in input_row_names:
        row_id = name_to_id.get(name)
        if row_id:
            task_rows.append(row_id)
        else:
            raise ValueError(f"Task row name '{name}' not found in the grid.")
    return task_rows


def get_prg_rows_to_copy(*, sheet: Sheet, input_row_names: list[str] | None) -> list[str]:
    prg_rows = []

    sheet_rows = sheet.rows
    if not input_row_names:
        # Copy all PRG rows if no input rows specified
        for row in sheet_rows:
            if row.type == CellType.PRG:
                prg_rows.append(row.row_id)
        return prg_rows

    name_to_id = {row.name: row.row_id for row in sheet_rows if row.name}
    for name in input_row_names:
        row_id = name_to_id.get(name)
        if row_id:
            prg_rows.append(row_id)
        else:
            raise ValueError(f"PRG row name '{name}' not found in the grid.")
    return prg_rows
