from __future__ import annotations

from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import Status
from albert.core.shared.identifiers import TaskId
from albert.core.shared.models.base import BaseResource


class BatchValuePatchDatum(BaseAlbertModel):
    """A single change applied to one cell of the batch data grid.

    Used within a :class:`BatchValuePatchPayload` to record the lot consumed for
    a batch value. See
    :meth:`~albert.collections.batch_data.BatchDataCollection.update_used_batch_amounts`.

    Attributes
    ----------
    attribute : str
        The field being changed. Defaults to ``"lotId"``.
    lot_id : str, optional
        The lot identifier being assigned, when applicable.
    new_value : str, optional
        The new value to set for the attribute.
    old_value : str, optional
        The previous value being replaced, when performing an update.
    operation : str
        The kind of change to apply (e.g. ``"add"``, ``"update"``, ``"delete"``).

    Examples
    --------
    !!! example
        ```python
        from albert.resources.batch_data import BatchValuePatchDatum

        datum = BatchValuePatchDatum(
            operation="update",
            new_value="LOT123",
            old_value="LOT100",
        )
        ```
    """

    attribute: str = Field(default="lotId")
    lot_id: str | None = Field(default=None, alias="lotId")
    new_value: str | None = Field(default=None, alias="newValue")
    old_value: str | None = Field(default=None, alias="oldValue")
    operation: str


class BatchValueId(BaseAlbertModel):
    """Locates a single cell (value) within the batch data grid.

    A value lives at the intersection of a row and a product column, so it is
    addressed by its row and (optionally) column identifiers.

    Attributes
    ----------
    row_id : str
        The identifier of the row the value belongs to. Required.
    col_id : str, optional
        The identifier of the product column the value belongs to.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.batch_data import BatchValueId

        location = BatchValueId(row_id="ROW1", col_id="COL1")
        ```
    """

    col_id: str | None = Field(default=None, alias="colId")
    row_id: str = Field(alias="rowId")


class BatchValuePatchPayload(BaseAlbertModel):
    """A batch of changes targeting one cell of the batch data grid.

    Passed to
    :meth:`~albert.collections.batch_data.BatchDataCollection.update_used_batch_amounts`
    to record which lots were used for recorded batch amounts.

    Attributes
    ----------
    id : BatchValueId
        Locates the cell to change (its row and optional column).
    data : list[BatchValuePatchDatum]
        The individual changes to apply to that cell.
    lot_id : str, optional
        The lot identifier associated with the change, when applicable.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.batch_data import (
            BatchValueId,
            BatchValuePatchDatum,
            BatchValuePatchPayload,
        )

        patch = BatchValuePatchPayload(
            id=BatchValueId(row_id="ROW1", col_id="COL1"),
            data=[BatchValuePatchDatum(operation="update", new_value="LOT123")],
        )
        ```
    """

    id: BatchValueId = Field(alias="Id")
    data: list[BatchValuePatchDatum] = Field(default_factory=list)
    lot_id: str | None = Field(default=None, alias="lotId")


class BatchDataType(str, Enum):
    """The kind of identifier used to look up batch data.

    Attributes
    ----------
    TASK_ID : str
        Look up batch data by the Task ID of its owning Batch Task.
    """

    TASK_ID = "taskId"


class BatchDataValue(BaseAlbertModel):
    """A single recorded amount within the batch data grid.

    Represents the value of one row within one product column (a cell of the
    grid), such as the amount of an ingredient used in a given batch.

    Attributes
    ----------
    id : str, optional
        The identifier of the value.
    col_id : str, optional
        The identifier of the product column this value belongs to.
    type : str, optional
        The type of the value.
    name : str, optional
        The display name associated with the value.
    value : str, optional
        The recorded amount.
    is_editable : bool, optional
        Whether the value can be edited.
    unit_category : str, optional
        The category of unit the value is expressed in.
    reference_value : str, optional
        The reference amount the value is compared against.
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
    """A row of the batch data grid, typically a formulation component.

    Each row represents an ingredient (or a sub-formula) that goes into the
    batch, together with the amounts recorded for it across the product columns.
    Sub-formulas expand into nested child rows.

    Attributes
    ----------
    id : str, optional
        The identifier of the row.
    row_id : str, optional
        The row identifier used to locate values (see :class:`BatchValueId`).
    type : str, optional
        The type of the row.
    name : str, optional
        The name of the component the row represents.
    manufacturer : str, optional
        The manufacturer of the component, when known.
    unit_category : str, optional
        The category of unit the row's amounts are expressed in.
    category : str, optional
        The category of the component.
    is_formula : bool, optional
        Whether the row represents a formula (as opposed to a raw material).
    is_lot_parent : bool, optional
        Whether the row groups lots as a parent row.
    values : list[BatchDataValue]
        The recorded amounts for this row, one per product column.
    child_rows : list[BatchDataRow]
        Nested rows, e.g. the components of a sub-formula.
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
    """A product column of the batch data grid.

    Each column represents the batch/product being manufactured, carrying its
    totals and any breakdown into individual lots.

    Attributes
    ----------
    id : str, optional
        The identifier of the column.
    name : str, optional
        The name of the product/batch.
    col_id : str, optional
        The column identifier used to locate values (see :class:`BatchValueId`).
    batch_total : str, optional
        The total amount recorded for the batch.
    reference_total : str, optional
        The reference total the batch is compared against.
    status : Status, optional
        The status of the column.
    product_total : float, optional
        The total amount of product produced.
    parent_id : str, optional
        The identifier of the parent column, when this column is a lot.
    design_col_id : str, optional
        The identifier of the corresponding design column.
    lots : list[BatchDataColumn]
        The individual lot columns that make up this product column.
    """

    # TODO: Once SignatureOverrideMeta removed, use BaseAlbertModel instead of BaseModel
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
    """The tabular record of how a batch of a formulation was made.

    Batch Data is the grid behind a Batch Task
    (:class:`~albert.resources.tasks.BatchTask`). It pairs formulation component
    rows with product columns; each cell holds the amount recorded for that
    component in that batch. It is retrieved by the owning Task ID via
    :class:`~albert.collections.batch_data.BatchDataCollection`
    (``client.batch_data``) and is not constructed directly.

    Attributes
    ----------
    id : str, optional
        The Task ID of the owning batch task (format ``TAS...``).
    size : int, optional
        The number of row entries in the batch data.
    last_key : str, optional
        Pagination cursor for fetching the next page of rows; pass it back as
        ``start_key`` to
        :meth:`~albert.collections.batch_data.BatchDataCollection.get_by_id`.
    product : list[BatchDataColumn], optional
        The product columns, one per batch/product being manufactured.
    rows : list[BatchDataRow], optional
        The formulation component rows.
    """

    id: TaskId | None = Field(default=None, alias="albertId")
    size: int | None = Field(default=None)
    last_key: str | None = Field(default=None, alias="lastKey")
    product: list[BatchDataColumn] | None = Field(default=None, alias="Product")
    rows: list[BatchDataRow] | None = Field(default=None, alias="Rows")
