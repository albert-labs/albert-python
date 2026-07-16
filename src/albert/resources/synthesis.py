from __future__ import annotations

from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import NotebookId, SynthesisId
from albert.core.shared.models.base import AuditFields


class ColumnDescriptor(BaseAlbertModel):
    """A single column in the reaction worksheet table.

    Attributes
    ----------
    id : str
        The column identifier.
    label : str, optional
        The human-readable column heading.
    category : str, optional
        The category the column belongs to.
    default : Any, optional
        The default value for cells in this column.
    type : str, optional
        The data type of the column's values.
    """

    id: str
    label: str | None = None
    category: str | None = None
    default: Any | None = None
    type: str | None = None


class ColumnSequence(BaseAlbertModel):
    """The ordered columns shown for reactants and products in the table.

    Attributes
    ----------
    reactants : list[ColumnDescriptor]
        The columns, in display order, for the reactant rows.
    products : list[ColumnDescriptor]
        The columns, in display order, for the product rows.
    """

    reactants: list[ColumnDescriptor] = Field(default_factory=list)
    products: list[ColumnDescriptor] = Field(default_factory=list)


class RowSequence(BaseAlbertModel):
    """The ordered row IDs for reactants and products in the table.

    Attributes
    ----------
    reactants : list[str]
        The reactant row IDs, in display order.
    products : list[str]
        The product row IDs, in display order.
    """

    reactants: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)


class ReactionParticipant(BaseAlbertModel):
    """A single reactant or product row in a reaction.

    Attributes
    ----------
    row_id : str
        The identifier of this row, used to target it in
        [`update_reactant_row_values`][albert.collections.synthesis.SynthesisCollection.update_reactant_row_values].
    smiles : str, optional
        The SMILES string of this participant's structure.
    values : dict, optional
        The quantities entered for this row, keyed by column.
    type : str, optional
        The kind of participant (for example, reactant or product).
    limiting_reagent : str or bool, optional
        Whether this participant is the limiting reagent.
    """

    row_id: str = Field(alias="rowId")
    smiles: str | None = None
    values: dict[str, Any] | None = None
    type: str | None = None
    limiting_reagent: str | bool | None = Field(default=None, alias="limitingReagent")


class Synthesis(BaseAlbertModel):
    """A synthesis (reaction) record documenting a chemical reaction.

    Captures a reaction drawn on a Ketcher canvas together with its reactant and
    product rows and their quantities. Retrieve one with
    [`get_by_id`][albert.collections.synthesis.SynthesisCollection.get_by_id], edit the
    updatable fields, and save with
    [`update`][albert.collections.synthesis.SynthesisCollection.update].

    Attributes
    ----------
    id : SynthesisId
        The Synthesis ID (format ``SYN...``).
    parent_id : NotebookId or str, optional
        The Notebook ID that owns this record (format ``NTB...``).
    name : str, optional
        The human-readable name of the synthesis.
    status : str, optional
        The status of the synthesis record.
    block_id : str, optional
        The Ketcher block ID this synthesis is associated with.
    inventory_id : str, optional
        The Inventory ID backing the reaction worksheet, set once the
        reactant/product table is initialized.
    hide_reaction_worksheet : str or bool, optional
        Whether the reaction worksheet table is hidden.
    s3_key : str, optional
        The storage key for the record's canvas assets.
    canvas_data : dict, optional
        The serialized Ketcher canvas data and preview image.
    smiles : list[str or None]
        The reaction SMILES strings for the drawn reaction.
    reactants : list[ReactionParticipant]
        The reactant rows of the reaction.
    products : list[ReactionParticipant]
        The product rows of the reaction.
    column_sequence : ColumnSequence, optional
        The ordered columns for the reactant and product tables.
    row_sequence : RowSequence, optional
        The ordered reactant and product row IDs.
    created : AuditFields, optional
        Audit information about when and by whom the record was created.
    updated : AuditFields, optional
        Audit information about the most recent update.
    """

    id: SynthesisId = Field(alias="albertId")
    parent_id: NotebookId | str | None = Field(default=None, alias="parentId")
    name: str | None = None
    status: str | None = None
    block_id: str | None = Field(default=None, alias="blockId")
    inventory_id: str | None = Field(default=None, alias="inventoryId")
    hide_reaction_worksheet: str | bool | None = Field(default=None, alias="hideReactionWorksheet")
    s3_key: str | None = Field(default=None, alias="s3Key")
    canvas_data: dict[str, Any] | None = Field(default=None, alias="canvasData")
    smiles: list[str | None] = Field(default_factory=list)
    reactants: list[ReactionParticipant] = Field(default_factory=list)
    products: list[ReactionParticipant] = Field(default_factory=list)
    column_sequence: ColumnSequence | None = Field(default=None, alias="columnSequence")
    row_sequence: RowSequence | None = Field(default=None, alias="rowSequence")
    created: AuditFields | None = Field(default=None, alias="Created")
    updated: AuditFields | None = Field(default=None, alias="Updated")


class ReactantValues(BaseAlbertModel):
    """The quantities entered for a single reactant row.

    Passed to
    [`update_reactant_row_values`][albert.collections.synthesis.SynthesisCollection.update_reactant_row_values]
    to set a reactant's amounts. Any field left as ``None`` is not set.

    !!! example
        ```python
        from albert.resources.synthesis import ReactantValues
        values = ReactantValues(mass=10.0, eq=1.0)
        ```

    Attributes
    ----------
    mass : float, optional
        The mass of the reactant.
    moles : float, optional
        The amount of the reactant in moles.
    eq : float, optional
        The number of equivalents of the reactant.
    concentration : float or int, optional
        The concentration of the reactant.
    """

    mass: float | None = None
    moles: float | None = None
    eq: float | None = None
    concentration: float | int | None = None
