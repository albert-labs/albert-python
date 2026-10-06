from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel


class InstructionRowType(str, Enum):
    """The kind of row an instruction item represents.

    Attributes
    ----------
    INVENTORY : str
        An ingredient row from the Product Design (a raw material in the formula).
    PARAMETER_GROUP : str
        A process group from the Process Design (a stage of the procedure, such
        as "Premix" or "Heating"). Only parameter group rows can be reordered.
    PARAMETER : str
        A measurement row inside a process group (a target or reading, such as
        temperature or mixing time).
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
    """One row of a formula's batch instructions.

    Instructions are the ordered rows that describe how a formula is made: its
    ingredient rows, its process groups (procedure stages), and the measurement
    rows inside them. Each row carries its per-column values in ``values``.
    """

    id: str | None = Field(default=None)
    """The ID of the entity behind the row (for example the ingredient's inventory
    ID, format ``INV...``, or the parameter ID)."""

    row_id: str | None = Field(default=None, alias="rowId")
    """The short ID of the row within its design (format ``ROW...``)."""

    row_unique_id: str | None = Field(default=None, alias="rowUniqueId")
    """The globally unique row ID, combining the design ID and row ID
    (format ``DES...#ROW...``). Used to identify rows when reordering."""

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
    """The batch instructions of a single formula inventory item.

    This is the ordered set of rows (ingredients, process groups, and
    measurements) that apply to one formula, along with the ``version`` used
    for reordering its process groups.
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
    """The globally unique row ID (format ``DES...#ROW...``)."""

    design_type: InstructionDesignType | None = Field(default=None, alias="designType")
    """The design the row comes from: ``products`` for ingredient rows,
    ``process`` for process rows."""

    is_hidden: bool | None = Field(default=None, alias="isHidden")
    """Whether the row is currently hidden on the Worksheet."""


class InstructionSequence(BaseAlbertModel):
    """The ordered instruction sequence of a formula inventory item.

    The sequence lists every instruction row in display order. Users can
    customize the order of process group rows; the result is stored alongside
    a ``version`` that is used to detect conflicting edits.
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
