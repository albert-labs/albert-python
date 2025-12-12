from __future__ import annotations

from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import NotebookId, SynthesisId
from albert.core.shared.models.base import AuditFields


class ColumnDescriptor(BaseAlbertModel):
    id: str
    label: str | None = None
    category: str | None = None
    default: Any | None = None
    type: str | None = None


class ColumnSequence(BaseAlbertModel):
    reactants: list[ColumnDescriptor] = Field(default_factory=list)
    products: list[ColumnDescriptor] = Field(default_factory=list)


class RowSequence(BaseAlbertModel):
    reactants: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)


class ReactionParticipant(BaseAlbertModel):
    row_id: str = Field(alias="rowId")
    smiles: str | None = None
    values: dict[str, Any] | None = None
    type: str | None = None
    limiting_reagent: str | bool | None = Field(default=None, alias="limitingReagent")


class Synthesis(BaseAlbertModel):
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
    mass: float | None = None
    moles: float | None = None
    eq: float | None = None
    concentration: float | int | None = None
