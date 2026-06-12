from __future__ import annotations

from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import Status
from albert.core.shared.identifiers import TaskId
from albert.core.shared.models.base import BaseResource


class BatchValuePatchDatum(BaseAlbertModel):
    """A single change descriptor in a batch value patch operation.

    Attributes
    ----------
    attribute : str
        The attribute being patched. Defaults to ``"lotId"``.
    lot_id : str | None
        The lot ID associated with this change.
    new_value : str | None
        The new value to set.
    old_value : str | None
        The previous value being replaced.
    operation : str
        The patch operation type (e.g. ``"update"``, ``"add"``, ``"delete"``).
    """

    attribute: str = Field(default="lotId")
    lot_id: str | None = Field(default=None, alias="lotId")
    new_value: str | None = Field(default=None, alias="newValue")
    old_value: str | None = Field(default=None, alias="oldValue")
    operation: str


class BatchValueId(BaseAlbertModel):
    """Identifies a cell in a batch data grid by column and row.

    Attributes
    ----------
    col_id : str | None
        The column identifier.
    row_id : str
        The row identifier.
    """

    col_id: str | None = Field(default=None, alias="colId")
    row_id: str = Field(alias="rowId")


class BatchValuePatchPayload(BaseAlbertModel):
    """Payload for patching a single batch data cell.

    Attributes
    ----------
    id : BatchValueId
        The cell coordinates (column and row).
    data : list[BatchValuePatchDatum]
        The list of change descriptors to apply.
    lot_id : str | None
        The lot ID to associate with this patch.
    """

    id: BatchValueId = Field(alias="Id")
    data: list[BatchValuePatchDatum] = Field(default_factory=list)
    lot_id: str | None = Field(default=None, alias="lotId")


class BatchDataType(str, Enum):
    """Type identifier used in batch data queries."""

    TASK_ID = "taskId"


class BatchDataValue(BaseAlbertModel):
    """A single cell value within a batch data row.

    Attributes
    ----------
    id : str | None
        The identifier of the value entry.
    col_id : str | None
        The column identifier.
    type : str | None
        The data type of the value.
    name : str | None
        The display name of the column.
    value : str | None
        The cell value.
    is_editable : bool | None
        Whether the cell is editable.
    unit_category : str | None
        The unit category for the value.
    reference_value : str | None
        The reference value for comparison purposes.
    """

    id: str | None = Field(default=None)
    col_id: str | None = Field(default=None, alias="colId")
    type: str | None = Field(default=None)
    name: str | None = Field(default=None)
    value: str | None = Field(default=None)
    is_editable: bool | None = Field(default=None, alias="isEditable")
    unit_category: str | None = Field(default=None, alias="unitCategory")
    reference_value: str | None = Field(default=None, alias="referenceValue")


class BatchDataRow(BaseAlbertModel):
    """A row of data in a batch task result.

    Attributes
    ----------
    id : str | None
        The identifier of the row entity.
    row_id : str | None
        The row identifier within the batch grid.
    type : str | None
        The row type (e.g. inventory category).
    name : str | None
        The display name of the row.
    manufacturer : str | None
        The manufacturer name, for inventory rows.
    unit_category : str | None
        The unit category used by this row.
    category : str | None
        The inventory category of the row.
    is_formula : bool | None
        Whether the row represents a formula inventory item.
    is_lot_parent : bool | None
        Whether this row is the parent of lot sub-rows.
    values : list[BatchDataValue]
        The cell values for this row.
    child_rows : list[BatchDataRow]
        Nested child rows (e.g. lot rows under a parent inventory row).
    """

    id: str | None = Field(default=None)
    row_id: str | None = Field(default=None, alias="rowId")
    type: str | None = Field(default=None)
    name: str | None = Field(default=None)
    manufacturer: str | None = Field(default=None)
    unit_category: str | None = Field(default=None, alias="unitCategory")
    category: str | None = Field(default=None)
    is_formula: bool | None = Field(default=None, alias="isFormula")
    is_lot_parent: bool | None = Field(default=None, alias="isLotParent")
    values: list[BatchDataValue] = Field(default_factory=list, alias="Values")
    child_rows: list[BatchDataRow] = Field(default_factory=list, alias="ChildRows")


class BatchDataColumn(BaseAlbertModel):
    # TODO: Once SignatureOverrideMeta removed, use BaseAlbertModel instead of BaseModel
    """A column in the batch data product grid, optionally containing lot sub-columns.

    Attributes
    ----------
    id : str | None
        The identifier of the inventory item for this column.
    name : str | None
        The display name of the column.
    col_id : str | None
        The column identifier within the batch grid.
    batch_total : str | None
        The total batch amount for this column.
    reference_total : str | None
        The reference total for this column.
    status : Status | None
        The status of the column.
    product_total : float | None
        The computed product total for this column.
    parent_id : str | None
        The parent column identifier, for lot sub-columns.
    design_col_id : str | None
        The design column identifier linking back to the worksheet.
    lots : list[BatchDataColumn]
        Lot-level sub-columns nested under this column.
    """

    id: str | None = Field(default=None)
    name: str | None = Field(default=None)
    col_id: str | None = Field(default=None, alias="colId")
    batch_total: str | None = Field(default=None, alias="batchTotal")
    reference_total: str | None = Field(default=None, alias="referenceTotal")
    status: Status | None = Field(default=None)
    product_total: float | None = Field(default=None, alias="productTotal")
    parent_id: str | None = Field(default=None, alias="parentId")
    design_col_id: str | None = Field(default=None, alias="designColId")
    lots: list[BatchDataColumn] = Field(default_factory=list, alias="Lots")


class BatchData(BaseResource):
    """The full batch data payload for a task, containing product columns and ingredient rows.

    Attributes
    ----------
    id : TaskId | None
        The Albert ID of the task this batch data belongs to.
    size : int | None
        The total number of items in this page of results.
    last_key : str | None
        Pagination cursor for fetching the next page.
    product : list[BatchDataColumn] | None
        The formulation columns (products) in the batch grid.
    rows : list[BatchDataRow] | None
        The ingredient rows in the batch grid.
    """

    id: TaskId | None = Field(default=None, alias="albertId")
    size: int | None = Field(default=None)
    last_key: str | None = Field(default=None, alias="lastKey")
    product: list[BatchDataColumn] | None = Field(default=None, alias="Product")
    rows: list[BatchDataRow] | None = Field(default=None, alias="Rows")
