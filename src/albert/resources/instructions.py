"""Models for the batching instructions of formulas.

Batching instructions describe how one specific formula is made as a batch.
They come in two layers, which this module's models reflect:

- The **procedure table** ([`InstructionLayout`][albert.resources.instructions.InstructionLayout]
  and [`InstructionRow`][albert.resources.instructions.InstructionRow]): the formula's
  ingredients, procedure stages (parameter groups), and readings (parameters),
  laid out as ordered rows with one value per relevant column. This is the table
  shown on the inventory details page in the Albert interface. Row content comes
  from the Worksheet and is edited there; the SDK reads the rows and can reorder
  the stages.
- The **instruction texts** ([`Instruction`][albert.resources.instructions.Instruction]):
  authored notes such as "Take the pH of the batch", attached to the formula as
  a whole or pinned to one ingredient row. These are created, renamed,
  reordered, copied between formulas, and deleted through the SDK.

Most models here are read-only views returned by the
[`InstructionsCollection`][albert.collections.instructions.InstructionsCollection]
(accessed as ``client.inventory.instructions``); only
[`Instruction`][albert.resources.instructions.Instruction] and
[`InstructionDesignLink`][albert.resources.instructions.InstructionDesignLink]
are constructed directly, to author instruction texts.
"""

from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import BaseResource


class InstructionRowType(str, Enum):
    """The kind of row in a formula's procedure table.

    In the Albert interface, ingredient and total rows are what you see in the
    formula table on the inventory details page, while parameter groups and
    parameters come from the Worksheet's Process Design.

    Attributes
    ----------
    INVENTORY : str
        An ingredient row: one component material of the formula, carrying its
        amount (and allowed range) per batch column.
    PARAMETER_GROUP : str
        A stage of the procedure, such as "Premix" or "Heating". Groups the
        parameter rows below it and is the only kind of row whose order can be
        customized per formula.
    PARAMETER : str
        A single reading or target inside a parameter group, such as
        temperature or mixing time. Moves with its parent group.
    BLANK : str
        A blank separator row from the Sheet design, used to visually group
        rows. Carries no recipe content and never appears in the row sequence.
    TOTAL : str
        The batch total row, which rolls up the ingredient amounts (for
        example the total batch size they sum to). The Albert interface uses
        it to display each ingredient as a percentage of the batch and does
        not list it among the instructions. Never appears in the row sequence.
    """

    INVENTORY = "INV"
    PARAMETER_GROUP = "PRG"
    PARAMETER = "PRM"
    BLANK = "BLK"
    TOTAL = "TOT"


class InstructionDesignType(str, Enum):
    """The Sheet design a sequenced row comes from.

    Attributes
    ----------
    PRODUCTS : str
        The Products design, which holds the formula's ingredient rows.
    PROCESS : str
        The Process design, which holds the procedure's parameter group and
        parameter rows.
    """

    PRODUCTS = "products"
    PROCESS = "process"


class SequencePosition(str, Enum):
    """Where to place a moved row relative to the reference row.

    Attributes
    ----------
    ABOVE : str
        Place the moved row directly above the reference row.
    BELOW : str
        Place the moved row directly below the reference row.
    """

    ABOVE = "above"
    BELOW = "below"


class InstructionValue(BaseAlbertModel):
    """One cell of a procedure row: the row's content for a single column.

    A row has one value per relevant column, for example the ingredient's
    amount in a given batch column, its manufacturer, or the row's batch
    instruction text. The ``type`` says which kind of content the value holds.

    Read-only; values are edited on the Worksheet.
    """

    id: str | None = Field(default=None)
    """The ID of the entity this value points at, when the value references one
    (for example the batch inventory ID on an amount cell)."""

    col_id: str | None = Field(default=None, alias="colId")
    """The ID of the Worksheet column this value belongs to (format ``COL...``)."""

    type: str | None = Field(default=None)
    """The kind of value: ``DEF`` for a defined column such as the row name,
    ``INV`` for an ingredient amount, ``BTI`` for the row's batch instruction
    text (the Batch Instruction column in the Albert interface), ``LKP`` for a
    looked-up attribute, or ``FNC`` for a calculated value."""

    name: str | None = Field(default=None)
    """The display name of the column this value belongs to."""

    value: str | dict[str, Any] | list[Any] | None = Field(default=None)
    """The cell content. Plain text for simple cells, or a structured object for
    rich values such as calculated amounts."""

    calculation: str | None = Field(default=None)
    """The calculation applied to this value, when one is defined."""

    min_value: str | None = Field(default=None, alias="minValue")
    """The lower bound of the acceptable range for this value, when defined."""

    max_value: str | None = Field(default=None, alias="maxValue")
    """The upper bound of the acceptable range for this value, when defined."""

    function: str | None = Field(default=None)
    """The inventory function applied to this value, when one is assigned."""

    attributes: str | dict[str, Any] | list[Any] | None = Field(default=None)
    """Additional attributes carried by this value, when present."""

    value_object: dict[str, Any] | None = Field(default=None, alias="ValueObject")
    """The structured result of a calculated (``FNC``) value, when present."""


class InstructionRow(BaseAlbertModel):
    """One row of a formula's procedure table.

    A row is one line of the procedure: an ingredient, a procedure stage
    (parameter group), a single reading (parameter), or a structural row
    (blank separator, batch total). ``type`` says which, and ``values`` carries
    the row's content per column.

    Read-only view returned by
    [`get_by_inventory_id`][albert.collections.instructions.InstructionsCollection.get_by_inventory_id].
    Row content is edited on the Worksheet; only the order of parameter group
    rows can be changed through the SDK, via
    [`update_sequence`][albert.collections.instructions.InstructionsCollection.update_sequence].
    """

    id: str | None = Field(default=None)
    """The ID of the entity behind the row: the ingredient's inventory ID
    (format ``INVA...``) for ingredient rows, the parameter group ID (format
    ``PRG...``) for parameter group rows, or the parameter ID for parameter
    rows. Useful for matching a row to an entity you already know."""

    row_id: str | None = Field(default=None, alias="rowId")
    """The short ID of the row within its design (format ``ROW...``)."""

    row_unique_id: str | None = Field(default=None, alias="rowUniqueId")
    """The globally unique row ID, combining the design ID and row ID
    (format ``DES...#ROW...``). This is the value to pass when reordering rows
    with
    [`update_sequence`][albert.collections.instructions.InstructionsCollection.update_sequence];
    match rows by ``name`` or ``id`` to find it."""

    type: InstructionRowType | None = Field(default=None)
    """The kind of row."""

    name: str | None = Field(default=None)
    """The display name of the row (for example the ingredient or stage name)."""

    original_name: str | None = Field(default=None, alias="originalName")
    """The row's original name before any renaming, when different."""

    row_hierarchy: list[str] | None = Field(default=None, alias="rowHierarchy")
    """The path of parent rows above this row, for nested rows."""

    unit_id: str | None = Field(default=None, alias="unitId")
    """The ID of the measurement unit for parameter rows (format ``UNI...``)."""

    unit_name: str | None = Field(default=None, alias="unitName")
    """The display name of the measurement unit for parameter rows."""

    label_name: str | None = Field(default=None, alias="labelName")
    """The display label for parameter rows, when defined."""

    category: str | None = Field(default=None)
    """The category ID of the parameter for parameter rows."""

    category_name: str | None = Field(default=None, alias="categoryName")
    """The display name of the parameter or parameter group category."""

    validation: dict[str, Any] | None = Field(default=None)
    """Validation rules configured on a parameter row, when present."""

    values: list[InstructionValue] | None = Field(default=None)
    """The row's cell values, one per relevant Worksheet column."""


class InstructionLayout(BaseAlbertModel):
    """The procedure table of a single formula: its rows with their values.

    Covers everything the formula's procedure involves, in display order:
    ingredients with their amounts, procedure stages and their readings, and
    any batch instruction text entered per row.

    Read-only view returned by
    [`get_by_inventory_id`][albert.collections.instructions.InstructionsCollection.get_by_inventory_id].
    The row order alone (without values) is available from
    [`get_sequence`][albert.collections.instructions.InstructionsCollection.get_sequence].
    """

    total: int | None = Field(default=None)
    """The number of rows in ``rows``."""

    inventory_id: str | None = Field(default=None, alias="inventoryId")
    """The ID of the formula the rows belong to (format ``INV...``)."""

    version: int | None = Field(default=None)
    """The current version of the row order. Pass this value when reordering
    rows so simultaneous edits are detected."""

    rows: list[InstructionRow] = Field(default_factory=list, alias="items")
    """The formula's rows in display order."""


class InstructionSequenceRow(BaseAlbertModel):
    """One row's place in the row order of a formula's batching instructions.

    Read-only view returned as part of
    [`InstructionSequence`][albert.resources.instructions.InstructionSequence].
    """

    row_id: str | None = Field(default=None, alias="rowId")
    """The globally unique row ID (format ``DES...#ROW...``). To find the ID for
    a row you know by name, match it in
    [`get_by_inventory_id`][albert.collections.instructions.InstructionsCollection.get_by_inventory_id]
    results and read its ``row_unique_id``."""

    design_type: InstructionDesignType | None = Field(default=None, alias="designType")
    """The Sheet design the row comes from: ``products`` for ingredient rows,
    ``process`` for parameter group and parameter rows."""

    is_hidden: bool | None = Field(default=None, alias="isHidden")
    """Whether the row is currently hidden on the Worksheet."""


class InstructionSequence(BaseAlbertModel):
    """The row order of a single formula's batching instructions.

    Lists every row of the formula's procedure in display order, along with the
    ``version`` used to detect conflicting edits. Ingredient rows always follow
    the order set on the Sheet's Products design, while parameter group rows
    can be reordered per formula via
    [`update_sequence`][albert.collections.instructions.InstructionsCollection.update_sequence].
    See
    [`InstructionsCollection`][albert.collections.instructions.InstructionsCollection]
    for the full picture of how the order is determined.

    Read-only view returned by
    [`get_sequence`][albert.collections.instructions.InstructionsCollection.get_sequence]
    and
    [`update_sequence`][albert.collections.instructions.InstructionsCollection.update_sequence].
    """

    id: str | None = Field(default=None)
    """The ID of the formula the sequence belongs to (format ``INV...``)."""

    version: int | None = Field(default=None)
    """The current version of the row order. Pass this value when reordering so
    simultaneous edits are detected."""

    is_overridden: bool | None = Field(default=None, alias="isOverridden")
    """Whether the order has been customized away from the Worksheet default."""

    rows: list[InstructionSequenceRow] = Field(default_factory=list, alias="sequence")
    """The rows in their current display order."""


class InstructionDesignLink(BaseAlbertModel):
    """Where an instruction text is pinned within a formula.

    Every instruction belongs to a formula (its parent). An instruction can
    additionally be pinned to one ingredient row of that formula; without a
    row link it is a formula-level instruction.
    """

    product_id: str | None = Field(default=None, alias="productId")
    """The ID of the formula the instruction belongs to (format ``INV...``)."""

    design_row_id: str | None = Field(default=None, alias="designRowId")
    """The unique ID of the ingredient row the instruction is pinned to
    (format ``DES...#ROW...``). When None, the instruction applies to the
    formula as a whole. Match rows by name in
    [`get_by_inventory_id`][albert.collections.instructions.InstructionsCollection.get_by_inventory_id]
    results and read their ``row_unique_id`` to find this value."""

    design_inv_id: str | None = Field(default=None, alias="designInvId")
    """Read-only. The inventory ID of the ingredient behind the linked row
    (format ``INVA...``), when the instruction is pinned to a row."""


class Instruction(BaseResource):
    """An authored instruction text on a formula.

    A free-text procedure note, such as "Take the pH of the batch", shown with
    the formula's batching instructions in the Albert interface. Every
    instruction belongs to exactly one formula (its ``parent_id``) and can
    optionally be pinned to one of the formula's ingredient rows via ``design``.

    Construct this model to author an instruction through
    [`create`][albert.collections.instructions.InstructionsCollection.create].
    ``id``, ``status``, ``created``, and ``updated`` are assigned by Albert and
    read-only. After creation, only ``name`` can be changed, via
    [`update`][albert.collections.instructions.InstructionsCollection.update].

    !!! example
        ```python
        from albert.resources.instructions import Instruction
        instruction = Instruction(name="Take the pH of the batch", parent_id="INV123")
        ```
    """

    name: str | None = Field(default=None, max_length=1000)
    """The instruction text (for example "Take the pH of the batch"). The only
    field that can be changed after creation."""

    parent_id: str | None = Field(default=None, alias="parentId")
    """The ID of the formula the instruction belongs to (format ``INV...``).
    Required at creation and fixed afterwards."""

    design: InstructionDesignLink | None = Field(default=None, alias="Design")
    """Where the instruction is pinned. Omit ``design_row_id`` for a
    formula-level instruction. Fixed at creation."""

    id: str | None = Field(default=None, alias="albertId")
    """Read-only. The Albert ID of the instruction (format ``ABI...``), assigned
    at creation."""


class InstructionOrder(BaseAlbertModel):
    """The display order of the instruction texts pinned to one row.

    Instruction texts are ordered independently within each pin: one order per
    ingredient row, plus one order for the formula-level instructions (the
    bucket with no ``design_row_id``).

    Read-only view returned as part of
    [`InstructionSet`][albert.resources.instructions.InstructionSet]. Change the
    order with
    [`update_row_sequence`][albert.collections.instructions.InstructionsCollection.update_row_sequence].
    """

    design_row_id: str | None = Field(default=None, alias="designRowId")
    """The unique ID of the ingredient row this order belongs to (format
    ``DES...#ROW...``). None marks the formula-level instructions."""

    instruction_ids: list[str] = Field(default_factory=list, alias="rowSequence")
    """The IDs of the pinned instructions in display order (format ``ABI...``)."""


class InstructionSet(BaseAlbertModel):
    """The instruction texts authored on a single formula, with their order.

    Read-only view returned by
    [`get_by_parent_ids`][albert.collections.instructions.InstructionsCollection.get_by_parent_ids]
    and
    [`update_row_sequence`][albert.collections.instructions.InstructionsCollection.update_row_sequence].
    """

    id: str | None = Field(default=None)
    """The ID of the formula the instructions belong to (format ``INV...``)."""

    parent_id: str | None = Field(default=None, alias="parentId")
    """The ID of the formula the instructions belong to (same as ``id``)."""

    instructions: list[Instruction] = Field(default_factory=list, alias="data")
    """The formula's instruction texts, in display order."""

    sequence: list[InstructionOrder] = Field(default_factory=list)
    """The per-row ordering of the formula's instruction texts."""


class InstructionCopyResult(BaseAlbertModel):
    """The outcome of copying instruction texts from one formula to others.

    Read-only view returned by
    [`copy`][albert.collections.instructions.InstructionsCollection.copy].
    """

    copied: int = Field(default=0)
    """The number of target formulas that received the instructions."""

    skipped: int = Field(default=0)
    """The number of target formulas skipped, for example because they already
    had instructions of their own."""
