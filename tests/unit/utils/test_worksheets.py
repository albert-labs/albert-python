"""Unit tests for worksheet copy-helper functions.

These use minimal duck-typed stand-ins for ``Sheet``/``Column``/``Row``/``Worksheet``
(narrow interfaces of just the attributes the functions read), rather than building
full ``Sheet`` objects with nested ``Design``/grid state that these functions never
touch.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from albert.resources.sheets import CellType
from albert.utils.worksheets import (
    get_columns_to_copy,
    get_prg_rows_to_copy,
    get_sheet_from_worksheet,
    get_task_rows_to_copy,
)


@dataclass
class _FakeColumn:
    column_id: str
    name: str | None = None
    pinned: str | None = None


@dataclass
class _FakeRow:
    row_id: str
    type: CellType | str
    name: str | None = None


@dataclass
class _FakeSheet:
    name: str
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)


@dataclass
class _FakeWorksheet:
    sheets: list


# ---------------------------------------------------------------------------
# get_sheet_from_worksheet
# ---------------------------------------------------------------------------


def test_get_sheet_from_worksheet_returns_matching_sheet():
    """Test that the sheet whose name matches is returned."""
    sheet_a = _FakeSheet(name="Sheet A")
    sheet_b = _FakeSheet(name="Sheet B")
    worksheet = _FakeWorksheet(sheets=[sheet_a, sheet_b])

    result = get_sheet_from_worksheet(sheet_name="Sheet B", worksheet=worksheet)

    assert result is sheet_b


def test_get_sheet_from_worksheet_raises_when_no_sheet_matches():
    """Test that an unmatched sheet name raises ValueError."""
    worksheet = _FakeWorksheet(sheets=[_FakeSheet(name="Sheet A")])

    with pytest.raises(ValueError, match="not found"):
        get_sheet_from_worksheet(sheet_name="Missing", worksheet=worksheet)


# ---------------------------------------------------------------------------
# get_columns_to_copy
# ---------------------------------------------------------------------------


def _sheet_with_columns() -> _FakeSheet:
    return _FakeSheet(
        name="Sheet A",
        columns=[
            _FakeColumn(column_id="COL1", name="Formulation A", pinned="left"),
            _FakeColumn(column_id="COL2", name="Formulation B", pinned=None),
            _FakeColumn(column_id="COL3", name="Formulation C", pinned=None),
        ],
    )


def test_get_columns_to_copy_both_flags_true_copies_every_column():
    """Test that setting both pinned and unpinned flags copies every column."""
    result = get_columns_to_copy(
        sheet=_sheet_with_columns(),
        copy_all_pinned_columns=True,
        copy_all_unpinned_columns=True,
        input_column_names=None,
    )

    assert set(result) == {"COL1", "COL2", "COL3"}


def test_get_columns_to_copy_pinned_only():
    """Test that copy_all_pinned_columns=True copies only pinned columns."""
    result = get_columns_to_copy(
        sheet=_sheet_with_columns(),
        copy_all_pinned_columns=True,
        copy_all_unpinned_columns=False,
        input_column_names=None,
    )

    assert set(result) == {"COL1"}


def test_get_columns_to_copy_unpinned_only():
    """Test that copy_all_unpinned_columns=True copies only unpinned columns."""
    result = get_columns_to_copy(
        sheet=_sheet_with_columns(),
        copy_all_pinned_columns=False,
        copy_all_unpinned_columns=True,
        input_column_names=None,
    )

    assert set(result) == {"COL2", "COL3"}


def test_get_columns_to_copy_neither_flag_uses_only_explicit_names():
    """Test that with both flags False, only explicitly named columns are copied."""
    result = get_columns_to_copy(
        sheet=_sheet_with_columns(),
        copy_all_pinned_columns=False,
        copy_all_unpinned_columns=False,
        input_column_names=["Formulation B"],
    )

    assert set(result) == {"COL2"}


def test_get_columns_to_copy_combines_flag_selection_with_explicit_names():
    """Test that explicit names are unioned with the flag-based selection."""
    result = get_columns_to_copy(
        sheet=_sheet_with_columns(),
        copy_all_pinned_columns=True,
        copy_all_unpinned_columns=False,
        input_column_names=["Formulation C"],
    )

    assert set(result) == {"COL1", "COL3"}


def test_get_columns_to_copy_raises_on_unknown_column_name():
    """Test that an unrecognized explicit column name raises ValueError."""
    with pytest.raises(ValueError, match="not found in sheet"):
        get_columns_to_copy(
            sheet=_sheet_with_columns(),
            copy_all_pinned_columns=False,
            copy_all_unpinned_columns=False,
            input_column_names=["Nonexistent"],
        )


# ---------------------------------------------------------------------------
# get_task_rows_to_copy
# ---------------------------------------------------------------------------


def _sheet_with_rows() -> _FakeSheet:
    return _FakeSheet(
        name="Sheet A",
        rows=[
            _FakeRow(row_id="ROW1", type=CellType.TAS, name="Task 1"),
            _FakeRow(row_id="ROW2", type=CellType.PRG, name="PG 1"),
            _FakeRow(row_id="ROW3", type=CellType.TAS, name="Task 2"),
        ],
    )


def test_get_task_rows_to_copy_returns_all_task_rows_by_default():
    """Test that omitting input_row_names copies every TAS-typed row."""
    result = get_task_rows_to_copy(sheet=_sheet_with_rows(), input_row_names=None)

    assert result == ["ROW1", "ROW3"]


def test_get_task_rows_to_copy_returns_named_rows_in_requested_order():
    """Test that explicit row names are resolved in the order given."""
    result = get_task_rows_to_copy(sheet=_sheet_with_rows(), input_row_names=["Task 2", "Task 1"])

    assert result == ["ROW3", "ROW1"]


def test_get_task_rows_to_copy_raises_on_unknown_row_name():
    """Test that an unrecognized explicit task row name raises ValueError."""
    with pytest.raises(ValueError, match="not found in the grid"):
        get_task_rows_to_copy(sheet=_sheet_with_rows(), input_row_names=["Missing Task"])


# ---------------------------------------------------------------------------
# get_prg_rows_to_copy
# ---------------------------------------------------------------------------


def test_get_prg_rows_to_copy_returns_all_prg_rows_by_default():
    """Test that omitting input_row_names copies every PRG-typed row."""
    result = get_prg_rows_to_copy(sheet=_sheet_with_rows(), input_row_names=None)

    assert result == ["ROW2"]


def test_get_prg_rows_to_copy_returns_named_rows():
    """Test that explicit row names resolve to their PRG row ids."""
    result = get_prg_rows_to_copy(sheet=_sheet_with_rows(), input_row_names=["PG 1"])

    assert result == ["ROW2"]


def test_get_prg_rows_to_copy_raises_on_unknown_row_name():
    """Test that an unrecognized explicit parameter-group row name raises ValueError."""
    with pytest.raises(ValueError, match="not found in the grid"):
        get_prg_rows_to_copy(sheet=_sheet_with_rows(), input_row_names=["Missing PG"])
