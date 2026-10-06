from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel


class InstructionRowType(str, Enum):
    """The kind of row in a formula's batching instructions.

    Attributes
    ----------
    INVENTORY : str
        An ingredient row from the Product Design (a raw material in the formula).
    PARAMETER_GROUP : str
        A parameter group from the Process Design (a stage of the procedure,
        such as "Premix" or "Heating"). Only parameter group rows can be
        reordered per formula.
    PARAMETER : str
        A parameter row inside a parameter group (a reading or target, such as
        temperature or mixing time). Parameter rows move with their parent group.
    BLOCK : str
        A block row. Blocks give structure but are not part of the reorderable sequence.
    TOTAL : str
        A total row that rolls up values across the formula.
    """

    INVENTORY = "INV"
    PARAMETER_GROUP = "PRG"
    PARAMETER = "PRM"
    BLOCK = "BLK"
    TOTAL = "TOT"


class InstructionDesignType(str, Enum):
    """The design a sequence row comes from.

    Attributes
    ----------
    PRODUCTS : str
        The Product Design, which holds the formula's ingredient rows.
    PROCESS : str
        The Process Design, which holds the procedure's parameter group rows.
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
    """A single cell of an instruction row.

    Each value belongs to one column of the Worksheet grid, so a row has one
    value per relevant column (for example the ingredient name, the manufacturer,
    or the amount used in a given batch column).
    """

    id: str | None = Field(default=None)
    """The ID of the entity this value points at, when the value references one
    (for example the batch inventory ID on an amount cell)."""

    col_id: str | None = Field(default=None, alias="colId")
    """The ID of the Worksheet column this value belongs to (format ``COL...``)."""

    type: str | None = Field(default=None)
    """The kind of value (for example ``DEF`` for a defined column, ``LKP`` for a
    lookup, ``INV`` for an inventory amount, or ``FNC`` for a calculated value)."""

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


class InstructionItem(BaseAlbertModel):
    """One row of a formula's batching instructions: an ingredient, a procedure
    stage, or a parameter.

    Batching instructions are the ordered rows that describe how one specific
    formula is made as a batch: its ingredient rows, its parameter groups
    (procedure stages), and the parameter rows inside them. Each row carries
    its per-column values in ``values``. The order of the rows is given by
    [`InstructionSequence`][albert.resources.instructions.InstructionSequence].
    """

    id: str | None = Field(default=None)
    """The ID of the entity behind the row: the ingredient's inventory ID
    (format ``INVA...``) for ingredient rows, the parameter group ID (format
    ``PRG...``) for procedure stage rows, or the parameter ID for parameter
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
    """The kind of row (ingredient, parameter group, parameter, block, or total)."""

    name: str | None = Field(default=None)
    """The display name of the row (for example the ingredient or step name)."""

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
    """The display name of the parameter or process group category."""

    validation: dict[str, Any] | None = Field(default=None)
    """Validation rules configured on a parameter row, when present."""

    values: list[InstructionValue] | None = Field(default=None)
    """The row's cell values, one per relevant Worksheet column."""


class InventoryInstructions(BaseAlbertModel):
    """The batching instructions of a single formula.

    This is the formula-specific procedure for making the formula as a batch:
    the ordered set of rows (ingredients, parameter groups, and parameters)
    that apply to it, along with the ``version`` used for reordering its
    parameter groups via
    [`update_sequence`][albert.collections.instructions.InstructionsCollection.update_sequence].
    """

    total: int | None = Field(default=None)
    """The number of instruction rows in ``items``."""

    inventory_id: str | None = Field(default=None, alias="inventoryId")
    """The ID of the formula inventory item these instructions belong to
    (format ``INV...``)."""

    version: int | None = Field(default=None)
    """The current version of the instruction sequence. Pass this value when
    reordering so simultaneous edits are detected."""

    items: list[InstructionItem] | None = Field(default=None)
    """The ordered instruction rows for the formula."""


class InstructionSequenceItem(BaseAlbertModel):
    """One row's place in a formula's instruction sequence."""

    row_id: str | None = Field(default=None, alias="rowId")
    """The globally unique row ID (format ``DES...#ROW...``). To find the ID for
    a row you know by name, match it in
    [`get_by_inventory_id`][albert.collections.instructions.InstructionsCollection.get_by_inventory_id]
    results and read its ``row_unique_id``."""

    design_type: InstructionDesignType | None = Field(default=None, alias="designType")
    """The design the row comes from: ``products`` for ingredient rows,
    ``process`` for process rows."""

    is_hidden: bool | None = Field(default=None, alias="isHidden")
    """Whether the row is currently hidden on the Worksheet."""


class InstructionSequence(BaseAlbertModel):
    """The ordered instruction sequence of a single formula.

    The sequence lists every row of the formula's procedure in display order.
    Ingredient rows always follow the order set on the Sheet's Product Design,
    while the order of parameter group rows can be customized per formula via
    [`update_sequence`][albert.collections.instructions.InstructionsCollection.update_sequence].
    See
    [`InstructionsCollection`][albert.collections.instructions.InstructionsCollection]
    for the full picture of how the order is determined. The sequence is stored
    alongside a ``version`` that is used to detect conflicting edits.
    """

    id: str | None = Field(default=None)
    """The ID of the formula inventory item the sequence belongs to (format ``INV...``)."""

    version: int | None = Field(default=None)
    """The current version of the sequence. Pass this value when reordering so
    simultaneous edits are detected."""

    is_overridden: bool | None = Field(default=None, alias="isOverridden")
    """Whether the order has been customized away from the Worksheet default."""

    sequence: list[InstructionSequenceItem] | None = Field(default=None)
    """The instruction rows in their current display order."""
