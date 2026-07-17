from __future__ import annotations

from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import NotebookId, SynthesisId
from albert.core.shared.models.base import AuditFields


class ColumnDescriptor(BaseAlbertModel):
    """A single column in the reaction worksheet table."""

    id: str
    """The column identifier."""

    label: str | None = None
    """The human-readable column heading."""

    category: str | None = None
    """The category the column belongs to."""

    default: Any | None = None
    """The default value for cells in this column."""

    type: str | None = None
    """The data type of the column's values."""


class ColumnSequence(BaseAlbertModel):
    """The ordered columns shown for reactants and products in the table."""

    reactants: list[ColumnDescriptor] = Field(default_factory=list)
    """The columns, in display order, for the reactant rows."""

    products: list[ColumnDescriptor] = Field(default_factory=list)
    """The columns, in display order, for the product rows."""


class RowSequence(BaseAlbertModel):
    """The ordered row IDs for reactants and products in the table."""

    reactants: list[str] = Field(default_factory=list)
    """The reactant row IDs, in display order."""

    products: list[str] = Field(default_factory=list)
    """The product row IDs, in display order."""


class ReactionParticipant(BaseAlbertModel):
    """A single reactant or product row in a reaction."""

    row_id: str = Field(alias="rowId")
    """The identifier of this row, used to target it in [`update_reactant_row_values`][albert.collections.synthesis.SynthesisCollection.update_reactant_row_values]."""

    smiles: str | None = None
    """The SMILES string of this participant's structure."""

    values: dict[str, Any] | None = None
    """The quantities entered for this row, keyed by column."""

    type: str | None = None
    """The kind of participant (for example, reactant or product)."""

    limiting_reagent: str | bool | None = Field(default=None, alias="limitingReagent")
    """Whether this participant is the limiting reagent."""


class Synthesis(BaseAlbertModel):
    """A synthesis (reaction) record documenting a chemical reaction.

    Captures a reaction drawn on a Ketcher canvas together with its reactant and
    product rows and their quantities. Retrieve one with
    [`get_by_id`][albert.collections.synthesis.SynthesisCollection.get_by_id], edit the
    updatable fields, and save with
    [`update`][albert.collections.synthesis.SynthesisCollection.update]."""

    id: SynthesisId = Field(alias="albertId")
    """The Synthesis ID (format ``SYN...``)."""

    parent_id: NotebookId | str | None = Field(default=None, alias="parentId")
    """The Notebook ID that owns this record (format ``NTB...``)."""

    name: str | None = None
    """The human-readable name of the synthesis."""

    status: str | None = None
    """The status of the synthesis record."""

    block_id: str | None = Field(default=None, alias="blockId")
    """The Ketcher block ID this synthesis is associated with."""

    inventory_id: str | None = Field(default=None, alias="inventoryId")
    """The Inventory ID backing the reaction worksheet, set once the reactant/product table is initialized."""

    hide_reaction_worksheet: str | bool | None = Field(default=None, alias="hideReactionWorksheet")
    """Whether the reaction worksheet table is hidden."""

    s3_key: str | None = Field(default=None, alias="s3Key")
    """The storage key for the record's canvas assets."""

    canvas_data: dict[str, Any] | None = Field(default=None, alias="canvasData")
    """The serialized Ketcher canvas data and preview image."""

    smiles: list[str | None] = Field(default_factory=list)
    """The reaction SMILES strings for the drawn reaction."""

    reactants: list[ReactionParticipant] = Field(default_factory=list)
    """The reactant rows of the reaction."""

    products: list[ReactionParticipant] = Field(default_factory=list)
    """The product rows of the reaction."""

    column_sequence: ColumnSequence | None = Field(default=None, alias="columnSequence")
    """The ordered columns for the reactant and product tables."""

    row_sequence: RowSequence | None = Field(default=None, alias="rowSequence")
    """The ordered reactant and product row IDs."""

    created: AuditFields | None = Field(default=None, alias="Created")
    """Audit information about when and by whom the record was created."""

    updated: AuditFields | None = Field(default=None, alias="Updated")
    """Audit information about the most recent update."""


class ReactantValues(BaseAlbertModel):
    """The quantities entered for a single reactant row.

    Passed to
    [`update_reactant_row_values`][albert.collections.synthesis.SynthesisCollection.update_reactant_row_values]
    to set a reactant's amounts. Any field left as ``None`` is not set.

    !!! example
        ```python
        from albert.resources.synthesis import ReactantValues
        values = ReactantValues(mass=10.0, eq=1.0)
        ```"""

    mass: float | None = None
    """The mass of the reactant."""

    moles: float | None = None
    """The amount of the reactant in moles."""

    eq: float | None = None
    """The number of equivalents of the reactant."""

    concentration: float | int | None = None
    """The concentration of the reactant."""
