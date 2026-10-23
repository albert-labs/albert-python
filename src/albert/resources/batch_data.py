from __future__ import annotations

from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.enums import Status
from albert.core.shared.identifiers import InventoryId, LotId, TaskId
from albert.core.shared.models.base import BaseResource


class BatchValuePatchDatum(BaseAlbertModel):
    """A single change applied to one cell of the batch data grid.

    Used within a [`BatchValuePatchPayload`][albert.resources.batch_data.BatchValuePatchPayload] to record the lot consumed for
    a batch value. See
    [`update_used_batch_amounts`][albert.collections.batch_data.BatchDataCollection.update_used_batch_amounts].

    Recording a lot's consumed amount is a two-step operation on the grid:
    first add the lot's child row under the ingredient (parent) row, then write
    the amount on the child row. Parent rows reject value writes
    (``400 "Parent row cannot be updated"``).

    !!! example
        ```python
        from albert.resources.batch_data import BatchValuePatchDatum

        # Step 1: add the lot child row under the ingredient row. The lot id
        # goes on this datum's `lot_id`; `new_value` is the numeric initial
        # amount ("0" is fine). `attribute` stays "lotId".
        add_lot = BatchValuePatchDatum(operation="add", lot_id="LOT123", new_value="0")

        # Step 2: write the recorded amount on the child row created above
        # (re-read the grid to discover its row id). `old_value` is required;
        # use "0" for the first write to a new lot row.
        write_amount = BatchValuePatchDatum(
            attribute="cell",
            operation="update",
            old_value="0",
            new_value="0.025",
        )
        ```"""

    attribute: str = Field(default="lotId")
    """The field being changed. Defaults to ``"lotId"`` (lot assignment; amounts use ``"cell"``)."""

    lot_id: str | None = Field(default=None, alias="lotId")
    """The lot to link when adding a lot child row (``operation="add"``, ``attribute="lotId"``).

    Required for that change: the lot is linked only when its id is set here.
    """

    new_value: str | None = Field(default=None, alias="newValue")
    """The new value to set for the attribute."""

    old_value: str | None = Field(default=None, alias="oldValue")
    """The previous value being replaced, when performing an update."""

    operation: str
    """The kind of change to apply (e.g. ``"add"``, ``"update"``, ``"delete"``)."""


class BatchValueId(BaseAlbertModel):
    """Locates a single cell (value) within the batch data grid.

    A value lives at the intersection of a row and a product column, so it is
    addressed by its row and (optionally) column identifiers.

    !!! example
        ```python
        from albert.resources.batch_data import BatchValueId

        location = BatchValueId(row_id="ROW1", col_id="COL9999999")
        ```"""

    col_id: str | None = Field(default=None, alias="colId")
    """The identifier of the product column the value belongs to."""

    row_id: str = Field(alias="rowId")
    """The identifier of the row the value belongs to. Required."""


class BatchValuePatchPayload(BaseAlbertModel):
    """A batch of changes targeting one cell of the batch data grid.

    Passed to
    [`update_used_batch_amounts`][albert.collections.batch_data.BatchDataCollection.update_used_batch_amounts]
    to record which lots were used for recorded batch amounts.

    !!! example
        ```python
        from albert.resources.batch_data import (
            BatchValueId,
            BatchValuePatchDatum,
            BatchValuePatchPayload,
        )

        # Step 1 of the lot flow: add the lot's child row under an ingredient
        # row. The lot id goes on the datum's `lot_id`; `new_value` is the
        # numeric initial amount.
        patch = BatchValuePatchPayload(
            id=BatchValueId(row_id="ROW1", col_id="COL9999999"),
            data=[BatchValuePatchDatum(operation="add", lot_id="LOT123", new_value="0")],
        )
        ```

    To confirm a lot was linked, re-read the grid: the new child row's ``id`` is
    the lot id. A child row with no ``id`` is not linked to any lot, so amounts
    written to it are not recorded against a lot. The child row's ``name`` can be
    blank even when the lot is linked.
    """

    id: BatchValueId = Field(alias="Id")
    """Locates the cell to change (its row and optional column)."""

    data: list[BatchValuePatchDatum] = Field(default_factory=list)
    """The individual changes to apply to that cell."""

    lot_id: str | None = Field(default=None, alias="lotId")
    """Not used to link a lot. Set ``lot_id`` on the
    [`BatchValuePatchDatum`][albert.resources.batch_data.BatchValuePatchDatum] instead:
    a lot id set only here adds a child row that is not linked to the lot."""


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
    grid), such as the amount of an ingredient used in a given batch."""

    id: str | None = Field(default=None)
    """The identifier of the value."""

    col_id: str | None = Field(default=None, alias="colId")
    """The identifier of the product column this value belongs to."""

    type: str | None = Field(default=None)
    """The type of the value."""

    name: str | None = Field(default=None)
    """The display name associated with the value."""

    value: str | None = Field(default=None)
    """The recorded amount."""

    is_editable: bool | None = Field(default=None, alias="isEditable")
    """Whether the value can be edited."""

    unit_category: str | None = Field(default=None, alias="unitCategory")
    """The category of unit the value is expressed in."""

    reference_value: str | None = Field(default=None, alias="referenceValue")
    """The reference amount the value is compared against."""


class BatchDataRow(BaseAlbertModel):
    """A row of the batch data grid, typically a formulation component.

    Each row represents an ingredient (or a sub-formula) that goes into the
    batch, together with the amounts recorded for it across the product columns.
    Sub-formulas expand into nested child rows."""

    id: str | None = Field(default=None)
    """The identifier of the row."""

    row_id: str | None = Field(default=None, alias="rowId")
    """The row identifier used to locate values (see [`BatchValueId`][albert.resources.batch_data.BatchValueId])."""

    type: str | None = Field(default=None)
    """The type of the row."""

    name: str | None = Field(default=None)
    """The name of the component the row represents."""

    manufacturer: str | None = Field(default=None)
    """The manufacturer of the component, when known."""

    unit_category: str | None = Field(default=None, alias="unitCategory")
    """The category of unit the row's amounts are expressed in."""

    category: str | None = Field(default=None)
    """The category of the component."""

    is_formula: bool | None = Field(default=None, alias="isFormula")
    """Whether the row represents a formula (as opposed to a raw material)."""

    is_lot_parent: bool | None = Field(default=None, alias="isLotParent")
    """Whether the row groups lots as a parent row."""

    values: list[BatchDataValue] = Field(default_factory=list, alias="Values")
    """The recorded amounts for this row, one per product column."""

    child_rows: list[BatchDataRow] = Field(default_factory=list, alias="ChildRows")
    """Nested rows, e.g. the components of a sub-formula."""


class BatchDataColumn(BaseAlbertModel):
    """A product column of the batch data grid.

    Each column represents the batch/product being manufactured, carrying its
    totals and any breakdown into individual lots."""

    # TODO: Once SignatureOverrideMeta removed, use BaseAlbertModel instead of BaseModel
    id: str | None = Field(default=None)
    """The identifier of the column."""

    name: str | None = Field(default=None)
    """The name of the product/batch."""

    col_id: str | None = Field(default=None, alias="colId")
    """The column identifier used to locate values (see [`BatchValueId`][albert.resources.batch_data.BatchValueId])."""

    batch_total: str | None = Field(default=None, alias="batchTotal")
    """The total amount recorded for the batch."""

    reference_total: str | None = Field(default=None, alias="referenceTotal")
    """The reference total the batch is compared against."""

    status: Status | None = Field(default=None)
    """The status of the column."""

    product_total: float | None = Field(default=None, alias="productTotal")
    """The total amount of product produced."""

    parent_id: str | None = Field(default=None, alias="parentId")
    """The identifier of the parent column, when this column is a lot."""

    design_col_id: str | None = Field(default=None, alias="designColId")
    """The identifier of the corresponding design column."""

    lots: list[BatchDataColumn] = Field(default_factory=list, alias="Lots")
    """The individual lot columns that make up this product column."""


class BatchData(BaseResource):
    """The tabular record of how a batch of a formulation was made.

    Batch Data is the grid behind a Batch Task
    ([`BatchTask`][albert.resources.tasks.BatchTask]). It pairs formulation component
    rows with product columns; each cell holds the amount recorded for that
    component in that batch. It is retrieved by the owning Task ID via
    [`BatchDataCollection`][albert.collections.batch_data.BatchDataCollection]
    (``client.batch_data``) and is not constructed directly."""

    id: TaskId | None = Field(default=None, alias="albertId")
    """The Task ID of the owning batch task (format ``TAS...``)."""

    size: int | None = Field(default=None)
    """The number of product columns in the batch data."""

    last_key: str | None = Field(default=None, alias="lastKey")
    """Pagination cursor for fetching the next page of product columns; pass it back as ``start_key`` to [`get_by_id`][albert.collections.batch_data.BatchDataCollection.get_by_id]."""

    product: list[BatchDataColumn] | None = Field(default=None, alias="Product")
    """The product columns, one per batch/product being manufactured."""

    rows: list[BatchDataRow] | None = Field(default=None, alias="Rows")
    """The formulation component rows."""


class BatchDataProduct(BaseAlbertModel):
    """A product column to add to, remove from, or reset in the batch data grid.

    The fields set identify the kind of column:

    - Inventory product column: set ``id`` to the Inventory ID (format ``INV...``).
    - Lookup column: set ``id`` and ``name``.
    - Batch Instructions block column: set ``name`` alone to add it, or ``col_id``
      to remove it.

    Columns of different kinds cannot be mixed in one call.

    !!! example
        ```python
        from albert.resources.batch_data import BatchDataProduct

        product = BatchDataProduct(id="INV123")
        ```
    """

    id: str | None = Field(default=None)
    """The Inventory ID of the product (format ``INV...``), or the ID of the lookup column."""

    name: str | None = Field(default=None)
    """The column name. Set alone to add a Batch Instructions block column; set with
    ``id`` for a lookup column."""

    col_id: str | None = Field(default=None, alias="colId")
    """The column ID (format ``COL...``), used to remove a Batch Instructions block column."""


class BatchDataDesign(BaseAlbertModel):
    """Locates a cell of a formulation design grid.

    A design cell is identified by its design (worksheet) ID together with its
    row and column IDs.

    !!! example
        ```python
        from albert.resources.batch_data import BatchDataDesign

        design = BatchDataDesign(id="DES100", row_id="ROW2", col_id="COL4")
        ```
    """

    id: str
    """The design ID of the formulation design."""

    row_id: str = Field(alias="rowId")
    """The row ID within the design."""

    col_id: str = Field(alias="colId")
    """The column ID within the design."""


class BatchDataDesignRow(BaseAlbertModel):
    """A design cell to add as a row of the batch data grid.

    !!! example
        ```python
        from albert.resources.batch_data import BatchDataDesign, BatchDataDesignRow

        row = BatchDataDesignRow(design=BatchDataDesign(id="DES100", row_id="ROW2", col_id="COL4"))
        ```
    """

    design: BatchDataDesign = Field(alias="Design")
    """The design cell to add as a row."""


class BatchDataRowCreated(BaseAlbertModel):
    """A row added to the batch data grid from a design cell."""

    task_id: str = Field(alias="taskId")
    """The owning batch task, in the form ``BTD#<Task ID>``."""

    design: BatchDataDesign = Field(alias="Design")
    """The design cell the row was added from."""

    row_id: str | None = Field(default=None, alias="rowId")
    """The ID of the newly created row (format ``ROW...``)."""

    inventory_id: str | None = Field(default=None, alias="inventoryId")
    """The Inventory ID of the component the row represents (format ``INV...``)."""


class BatchDataLotProduct(BaseAlbertModel):
    """A product whose batch data references a given lot."""

    id: str
    """The Inventory ID of the product (format ``INV...``)."""

    lot_id: str | None = Field(default=None, alias="lotId")
    """The Lot ID recorded for the product (format ``LOT...``), when the reference is a lot pick."""


class BatchDataLotUsage(BaseAlbertModel):
    """A batch task and product that reference a given lot.

    Returned by
    [`get_by_lot_id`][albert.collections.batch_data.BatchDataCollection.get_by_lot_id]
    to show where a lot was consumed."""

    task_id: str = Field(alias="parentId")
    """The Task ID of the batch task (format ``TAS...``)."""

    product: BatchDataLotProduct = Field(alias="Product")
    """The product referencing the lot."""


class RawCostEntry(BaseAlbertModel):
    """A formula lot whose raw material cost is recalculated from a batch task.

    The raw cost is computed from the amounts and costs of the ingredient lots
    consumed in the given batch task, divided by the batch size.

    !!! example
        ```python
        from albert.resources.batch_data import RawCostEntry

        entry = RawCostEntry(task_id="TAS123", product_id="INV456", lot_id="LOT789")
        ```
    """

    task_id: TaskId
    """The Task ID of the batch task whose consumed lots determine the cost
    (format ``TAS...``)."""

    product_id: InventoryId
    """The Inventory ID of the formula product (format ``INV...``)."""

    lot_id: LotId
    """The Lot ID of the formula lot to price (format ``LOT...``)."""

    updated_at: str | None = Field(default=None, alias="updatedAt")
    """Optimistic concurrency timestamp (ISO 8601). When set, the recalculation is
    skipped if the batch data column changed since this time."""


class ReactionBatchDataProject(BaseAlbertModel):
    """The project a reaction batch task belongs to."""

    project_id: str = Field(alias="projectId")
    """The Project ID (format ``PRO...``)."""

    project_name: str | None = Field(default=None, alias="projectName")
    """The project name, when available."""


class ReactionLot(BaseAlbertModel):
    """The lot picked for a reagent of a reaction batch task."""

    lot_id: str = Field(alias="lotId")
    """The Lot ID of the picked lot (format ``LOT...``)."""

    inventory_id: str | None = Field(default=None, alias="inventoryId")
    """The Inventory ID the lot belongs to (format ``INV...``)."""

    substance_id: str | None = Field(default=None, alias="substanceId")
    """The substance ID of the reagent."""

    amt: float | None = Field(default=None)
    """The amount of the lot consumed."""

    unit: str | None = Field(default=None)
    """The unit the consumed amount is expressed in."""

    inventory_on_hand: float | None = Field(default=None, alias="inventoryOnHand")
    """The remaining on-hand quantity of the lot."""

    albert_id: str | None = Field(default=None, alias="albertId")
    """The Albert ID of the lot."""

    lot_number: str | None = Field(default=None, alias="lotNumber")
    """The lot number."""

    parent_name: str | None = Field(default=None, alias="parentName")
    """The name of the inventory item the lot belongs to."""


class ReactionReagent(BaseAlbertModel):
    """A reagent of a reaction batch task, with its planned and picked amounts."""

    stt_id: str = Field(alias="sttId")
    """The substance ID of the reagent."""

    name: str | None = Field(default=None)
    """The display name of the reagent."""

    function: str | None = Field(default=None)
    """The role of the reagent in the reaction (e.g. solvent, catalyst)."""

    is_limiting_reagent: bool | None = Field(default=None, alias="isLimitingReagent")
    """Whether the reagent limits the reaction yield."""

    eq: str | None = Field(default=None)
    """The equivalents display string. Do not parse as a number."""

    mw: float | None = Field(default=None)
    """The molecular weight of the reagent."""

    purity: float | None = Field(default=None)
    """The purity of the reagent."""

    total_amt: float | None = Field(default=None, alias="totalAmt")
    """The planned amount of the reagent."""

    unit: str | None = Field(default=None)
    """The unit amounts are expressed in."""

    total_used: float | None = Field(default=None, alias="totalUsed")
    """The amount of the reagent used so far (the picked lot amount)."""

    smiles: str | None = Field(default=None)
    """The SMILES structure string of the reagent."""

    image_url: str | None = Field(default=None, alias="imageUrl")
    """The URL of the reagent's structure image."""

    lot: ReactionLot | None = Field(default=None, alias="Lot")
    """The lot picked for the reagent; ``None`` until a lot is picked."""


class ReactionProduct(BaseAlbertModel):
    """A product of a reaction batch task, with its planned and actual amounts."""

    stt_id: str = Field(alias="sttId")
    """The substance ID of the product."""

    name: str | None = Field(default=None)
    """The display name of the product."""

    sub_id: str | None = Field(default=None, alias="subId")
    """The sub ID assigned to the product."""

    mw: float | None = Field(default=None)
    """The molecular weight of the product."""

    actual: float | None = Field(default=None)
    """The actual amount of product obtained (the recorded yield)."""

    total_amt: float | None = Field(default=None, alias="totalAmt")
    """The planned amount of the product."""

    unit: str | None = Field(default=None)
    """The unit amounts are expressed in."""

    smiles: str | None = Field(default=None)
    """The SMILES structure string of the product."""

    image_url: str | None = Field(default=None, alias="imageUrl")
    """The URL of the product's structure image."""


class Reaction(BaseAlbertModel):
    """A single reaction of a reaction batch task."""

    id: str
    """The reaction ID (format ``RXN...``)."""

    name: str | None = Field(default=None)
    """The display name of the reaction."""

    reagents: list[ReactionReagent] = Field(default_factory=list, alias="Reagents")
    """The reagents of the reaction."""

    products: list[ReactionProduct] = Field(default_factory=list, alias="Products")
    """The products of the reaction."""


class ReactionBatchData(BaseAlbertModel):
    """The reaction grid of a reaction batch task.

    Pairs each reaction's reagents (with their picked lots) and products (with
    their actual amounts) for a reaction Batch Task. Retrieved with
    [`get_reaction`][albert.collections.batch_data.BatchDataCollection.get_reaction].

    (🧪 Beta) Requires the reaction batch task feature to be enabled for the tenant.
    """

    task_id: str = Field(alias="taskId")
    """The Task ID of the owning batch task (format ``TAS...``)."""

    state: str | None = Field(default=None)
    """The state of the owning task (e.g. ``In Progress``); ``None`` when the task
    state could not be read."""

    locked: bool | None = Field(default=None)
    """Whether the grid is read-only (the task is Completed or Closed)."""

    project: ReactionBatchDataProject | None = Field(default=None, alias="Project")
    """The project the task belongs to, when it has one."""

    reactions: list[Reaction] = Field(default_factory=list, alias="Reactions")
    """The reactions of the task; empty when the reaction snapshot has not been created."""


class ReactionLotPick(BaseAlbertModel):
    """The lot picked for a reagent, with the amount consumed.

    !!! example
        ```python
        from albert.resources.batch_data import ReactionLotPick

        pick = ReactionLotPick(lot_id="LOT123", amt=2.5, unit="g")
        ```
    """

    lot_id: LotId = Field(alias="lotId")
    """The Lot ID to pick (format ``LOT...``). Required."""

    inventory_id: InventoryId | None = Field(default=None, alias="inventoryId")
    """The Inventory ID the lot belongs to (format ``INV...``)."""

    substance_id: str | None = Field(default=None, alias="substanceId")
    """The substance ID of the reagent."""

    amt: float
    """The amount of the lot consumed. Required."""

    unit: str | None = Field(default=None)
    """The unit the consumed amount is expressed in."""


class ReactionValueId(BaseAlbertModel):
    """Locates a reagent or product row within a reaction of a reaction batch task.

    !!! example
        ```python
        from albert.resources.batch_data import ReactionValueId

        location = ReactionValueId(reaction_id="RXN1826", stt_id="STT1f13")
        ```
    """

    reaction_id: str = Field(alias="reactionId")
    """The reaction ID (format ``RXN...``)."""

    stt_id: str = Field(alias="sttId")
    """The substance ID of the reagent or product."""


class ReactionValuePatchDatum(BaseAlbertModel):
    """A single change to a reagent or product of a reaction batch task.

    The supported changes are:

    - Pick a lot for a reagent: ``operation="add"``, ``attribute="lot"``,
      ``new_value`` a [`ReactionLotPick`][albert.resources.batch_data.ReactionLotPick].
      Picking a lot moves inventory immediately. One lot per reagent.
    - Remove the lot pick: ``operation="delete"``, ``attribute="lot"``.
    - Change the picked amount: ``operation="update"``, ``attribute="amt"``,
      ``new_value`` a number.
    - Set a product's sub ID: ``operation="update"``, ``attribute="subId"``,
      ``new_value`` a string.
    - Record a product's actual yield: ``operation="update"``, ``attribute="actual"``,
      ``new_value`` a number (``0`` is valid).

    !!! example
        ```python
        from albert.resources.batch_data import ReactionLotPick, ReactionValuePatchDatum

        pick = ReactionValuePatchDatum(
            operation="add",
            attribute="lot",
            new_value=ReactionLotPick(lot_id="LOT123", amt=2.5, unit="g"),
        )
        ```
    """

    operation: str
    """The kind of change to apply (``"add"``, ``"update"``, or ``"delete"``)."""

    attribute: str
    """The field being changed (``"lot"``, ``"amt"``, ``"subId"``, or ``"actual"``)."""

    new_value: ReactionLotPick | float | str | None = Field(default=None, alias="newValue")
    """The new value for the change. A
    [`ReactionLotPick`][albert.resources.batch_data.ReactionLotPick] when picking a lot;
    a number for ``amt``/``actual``; a string for ``subId``. Unused for ``delete``."""


class ReactionValuePatchPayload(BaseAlbertModel):
    """A batch of changes targeting one reagent or product of a reaction batch task.

    !!! example
        ```python
        from albert.resources.batch_data import (
            ReactionLotPick,
            ReactionValueId,
            ReactionValuePatchDatum,
            ReactionValuePatchPayload,
        )

        patch = ReactionValuePatchPayload(
            id=ReactionValueId(reaction_id="RXN1826", stt_id="STT1f13"),
            data=[
                ReactionValuePatchDatum(
                    operation="add",
                    attribute="lot",
                    new_value=ReactionLotPick(lot_id="LOT123", amt=2.5, unit="g"),
                )
            ],
        )
        ```
    """

    id: ReactionValueId = Field(alias="Id")
    """Locates the reagent or product to change."""

    data: list[ReactionValuePatchDatum]
    """The individual changes to apply."""


class ReactionCompleteResult(BaseAlbertModel):
    """The outcome of completing a reaction batch task.

    Completing a reaction task creates the output lot for the reaction product
    and stamps the task completion date. Completion is idempotent: repeating it
    returns the already-created output lot with ``replay`` set to ``True``."""

    task_id: str = Field(alias="taskId")
    """The Task ID of the completed batch task (format ``TAS...``)."""

    reaction_id: str | None = Field(default=None, alias="reactionId")
    """The reaction ID that was completed (format ``RXN...``)."""

    inventory_id: str | None = Field(default=None, alias="inventoryId")
    """The Inventory ID of the reaction output (format ``INV...``)."""

    lot_id: str = Field(alias="lotId")
    """The Lot ID of the output lot (format ``LOT...``)."""

    inventory_on_hand: str | None = Field(default=None, alias="inventoryOnHand")
    """The on-hand quantity of the output lot. Only set on the first completion."""

    replay: bool | None = Field(default=None)
    """``True`` when the task was already completed and no new lot was created."""
