from __future__ import annotations

from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import NotebookId, SynthesisId
from albert.core.shared.models.base import AuditFields


class ColumnDescriptor(BaseAlbertModel):
    """A descriptor for a column in a synthesis reaction table.

    Attributes
    ----------
    id : str
        The column identifier.
    label : str | None
        The display label for the column.
    category : str | None
        The category of the column.
    default : Any | None
        The default value for the column.
    type : str | None
        The data type of the column.
    """

    id: str
    label: str | None = None
    category: str | None = None
    default: Any | None = None
    type: str | None = None


class ColumnSequence(BaseAlbertModel):
    """The ordered column layout for reactants and products in a synthesis table.

    Attributes
    ----------
    reactants : list[ColumnDescriptor]
        Column descriptors for the reactant side of the reaction.
    products : list[ColumnDescriptor]
        Column descriptors for the product side of the reaction.
    """

    reactants: list[ColumnDescriptor] = Field(default_factory=list)
    products: list[ColumnDescriptor] = Field(default_factory=list)


class RowSequence(BaseAlbertModel):
    """The ordered row layout for reactants and products in a synthesis table.

    Attributes
    ----------
    reactants : list[str]
        Row IDs for the reactant rows.
    products : list[str]
        Row IDs for the product rows.
    """

    reactants: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)


class ReactionParticipant(BaseAlbertModel):
    """A single reactant or product entry in a synthesis reaction.

    Attributes
    ----------
    row_id : str
        The row identifier within the synthesis table.
    smiles : str | None
        The SMILES notation for the chemical structure.
    values : dict[str, Any] | None
        The stoichiometric and property values for this participant.
    type : str | None
        The participant type (e.g. reactant or product).
    limiting_reagent : str | bool | None
        Whether this participant is the limiting reagent.
    """

    row_id: str = Field(alias="rowId")
    smiles: str | None = None
    values: dict[str, Any] | None = None
    type: str | None = None
    limiting_reagent: str | bool | None = Field(default=None, alias="limitingReagent")


class Synthesis(BaseAlbertModel):
    """A synthesis reaction record embedded within a notebook block.

    Attributes
    ----------
    id : SynthesisId
        The Albert ID of the synthesis.
    parent_id : NotebookId | str | None
        The Albert ID of the parent notebook.
    name : str | None
        The name of the synthesis.
    status : str | None
        The status of the synthesis.
    block_id : str | None
        The notebook block ID containing this synthesis.
    inventory_id : str | None
        The inventory item ID associated with the product of this synthesis.
    hide_reaction_worksheet : str | bool | None
        Whether the reaction worksheet is hidden in the UI.
    s3_key : str | None
        The S3 storage key for the Ketcher canvas data file.
    canvas_data : dict[str, Any] | None
        The Ketcher canvas state for the reaction drawing.
    smiles : list[str | None]
        SMILES strings extracted from the reaction.
    reactants : list[ReactionParticipant]
        The reactant entries in the synthesis reaction.
    products : list[ReactionParticipant]
        The product entries in the synthesis reaction.
    column_sequence : ColumnSequence | None
        The column layout for the synthesis table.
    row_sequence : RowSequence | None
        The row layout for the synthesis table.
    created : AuditFields | None
        Audit fields for when the synthesis was created.
    updated : AuditFields | None
        Audit fields for the last update.
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
    """Stoichiometric values for a reactant in a synthesis calculation.

    Attributes
    ----------
    mass : float | None
        The mass of the reactant.
    moles : float | None
        The moles of the reactant.
    eq : float | None
        The equivalents relative to the limiting reagent.
    concentration : float | int | None
        The concentration of the reactant in solution.
    """

    mass: float | None = None
    moles: float | None = None
    eq: float | None = None
    concentration: float | int | None = None
