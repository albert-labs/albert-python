from __future__ import annotations

import sys
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, model_serializer, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
    DataTemplateId,
    DesignSpaceId,
    InventoryId,
    ParameterGroupId,
    ParameterId,
    ProjectId,
    SmartDatasetId,
    UnitId,
)
from albert.core.shared.models.base import AuditFields, BaseResource

if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
    from enum import StrEnum
else:  # pragma: no cover (py311+)
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class DesignSpaceState(StrEnum):
    """Lifecycle of a design space. Orthogonal to its soft-delete ``status``."""

    DRAFT = "draft"
    PUBLISHED = "published"


class IngredientAction(StrEnum):
    """How an ingredient participates in formulations drawn from a design space."""

    MUST_INCLUDE = "mustInclude"
    MAY_INCLUDE = "mayInclude"
    EXCLUDE = "exclude"


class ParameterDataType(StrEnum):
    """The kind of values a design-space parameter takes."""

    NUMERIC = "numeric"
    CATEGORICAL = "categorical"


class DesignSpaceViolationCode(StrEnum):
    """Machine-readable category of a design-space validation finding."""

    INFEASIBLE_DESIGN_SPACE = "infeasible_design_space"
    UNKNOWN_REFERENCE = "unknown_reference"
    INVALID_CONSTRAINT = "invalid_constraint"
    FEASIBILITY_INDETERMINATE = "feasibility_indeterminate"
    DIMENSION_NOT_IN_DATASET = "dimension_not_in_dataset"
    DIMENSION_NOT_MODELLED = "dimension_not_modelled"
    DUPLICATE_CONSTRAINT_SUBJECT = "duplicate_constraint_subject"
    VARIABLE_NOT_DERIVED = "variable_not_derived"
    INTERNAL = "internal"


class ContinuousConstraint(BaseAlbertModel):
    """A numeric parameter restricted to a range. Either bound may be omitted."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["continuous"] = "continuous"
    """Constraint kind; fixed to ``continuous``."""

    min: float | None = Field(default=None)
    """Smallest allowed value. Omit for no lower bound."""

    max: float | None = Field(default=None)
    """Largest allowed value. Omit for no upper bound."""


class DiscreteConstraint(BaseAlbertModel):
    """A numeric parameter restricted to an explicit set of numbers."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["discrete"] = "discrete"
    """Constraint kind; fixed to ``discrete``."""

    values: list[float] = Field(min_length=1)
    """The allowed values."""


class CategoricalConstraint(BaseAlbertModel):
    """A parameter restricted to an explicit set of category labels."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["categorical"] = "categorical"
    """Constraint kind; fixed to ``categorical``."""

    values: list[str] = Field(min_length=1)
    """The allowed category labels."""


ParameterConstraint = Annotated[
    ContinuousConstraint | DiscreteConstraint | CategoricalConstraint,
    Field(discriminator="type"),
]
"""The allowed values of a design-space parameter: a continuous range, a discrete set
of numbers, or a set of categories."""


class IngredientEntry(BaseAlbertModel):
    """An ingredient dimension of a design space: its action plus fraction bounds."""

    action: IngredientAction
    """``mustInclude`` pins the ingredient into every formulation, ``mayInclude`` leaves
    it optional, and ``exclude`` bans it. An excluded ingredient keeps its ``min`` and
    ``max``, but they are not applied while it is excluded; they apply again once the
    action changes back to ``mayInclude`` or ``mustInclude``."""

    min: float | None = Field(default=None, ge=0, le=1)
    """Fraction lower bound (0 to 1)."""

    max: float | None = Field(default=None, ge=0, le=1)
    """Fraction upper bound (0 to 1)."""


class ParameterRef(BaseAlbertModel):
    """The structured identity of a parameter: where it lives, and in what unit."""

    parameter_id: ParameterId = Field(alias="parameterId")
    """The parameter (format ``PRM...``)."""

    data_template_id: DataTemplateId | None = Field(default=None, alias="dataTemplateId")
    """The data template (format ``DAT...``) the parameter belongs to. Exactly one of
    ``data_template_id`` / ``parameter_group_id`` is set."""

    parameter_group_id: ParameterGroupId | None = Field(default=None, alias="parameterGroupId")
    """The parameter group (format ``PRG...``) the parameter belongs to. Exactly one of
    ``data_template_id`` / ``parameter_group_id`` is set."""

    unit_id: UnitId | None = Field(default=None, alias="unitId")
    """The unit (format ``UNI...``) the parameter is expressed in; ``None`` when the
    parameter is unit-less."""


class ParameterEntry(BaseAlbertModel):
    """A parameter dimension of a design space: its identity plus allowed values."""

    ref: ParameterRef
    """The parameter's structured identity."""

    data_type: ParameterDataType = Field(alias="dataType")
    """Whether the parameter is numeric or categorical."""

    constraint: ParameterConstraint
    """The values the parameter may take inside the space."""


class DesignSpace(BaseResource):
    """A design space: the bounded envelope a design run samples formulations from.

    Also called the search space or simply the bounds: which ingredients may or must
    appear, the fraction range of each, the allowed values of parameters, and how many
    ingredients one formulation may carry.

    A space is created as a draft, edited with builder operations, checked for
    feasibility, and published. A published space is frozen; editing one means forking
    it into a new draft.
    """

    id: DesignSpaceId | None = Field(default=None)
    """The unique identifier of the design space (format ``DSP...``)."""

    schema_version: int | None = Field(default=None, alias="schemaVersion")
    """Which document shape the record follows. Not a concurrency counter."""

    name: str | None = Field(default=None, min_length=1)
    """Display name of the design space."""

    description: str | None = Field(default=None)
    """Free-text description of the space's intent."""

    parent_id: ProjectId | None = Field(default=None, alias="parentId")
    """The project (format ``PRO...``) that owns the space and controls access to it."""

    state: DesignSpaceState | None = Field(default=None)
    """Lifecycle state: ``draft`` (editable) or ``published`` (frozen)."""

    published_at: datetime | None = Field(default=None, alias="publishedAt")
    """When the space was published; ``None`` while it is a draft."""

    forked_from_id: DesignSpaceId | None = Field(default=None, alias="forkedFromId")
    """The published design space this draft was forked from, if any."""

    derived_from_id: SmartDatasetId | None = Field(default=None, alias="derivedFromId")
    """The smart dataset (format ``SDT...``) that seeded the first draft, if any.
    Provenance only; the space does not track the dataset afterwards."""

    min_count: int | None = Field(default=None, ge=0, alias="minCount")
    """Least ingredients in one formulation. ``None`` leaves the count unbounded below."""

    max_count: int | None = Field(default=None, ge=0, alias="maxCount")
    """Most ingredients in one formulation. ``None`` leaves the count unbounded above."""

    ingredients: dict[InventoryId, IngredientEntry] | None = Field(default=None)
    """Ingredient dimensions, keyed by inventory ID (format ``INV...``). Empty when absent."""

    parameters: dict[str, ParameterEntry] | None = Field(default=None)
    """Parameter dimensions, keyed by the composite parameter key. Empty when absent."""

    version: int | None = Field(default=None)
    """Optimistic-concurrency counter, checked on every write."""

    created: AuditFields | None = Field(default=None, alias="created", frozen=True)
    """Audit fields for the creation of the design space."""

    updated: AuditFields | None = Field(default=None, alias="updated", frozen=True)
    """Audit fields for the last update of the design space."""


class DesignSpaceViolation(BaseAlbertModel):
    """A single design-space validation finding."""

    code: DesignSpaceViolationCode
    """Machine-readable category of the finding."""

    message: str
    """Human-readable explanation of the finding."""

    target_id: str | None = Field(default=None, alias="targetId")
    """The component or dimension the finding is scoped to, when applicable."""

    components: list[str] | None = Field(default=None)
    """Component paths (``<collection>/<key>``) the finding is attributed to."""

    op_index: int | None = Field(default=None, alias="opIndex")
    """Position in the request's ``operations`` of the operation behind the finding.

    Set on findings from [`apply`][albert.collections.design_spaces.DesignSpaceCollection.apply];
    ``None`` when the finding is not tied to an operation.
    """


class DesignSpaceCreated(DesignSpace):
    """A newly created draft design space, with any findings from seeding it."""

    warnings: list[DesignSpaceViolation] = Field(default_factory=list)
    """Non-blocking findings from seeding the draft from a smart dataset: one
    ``variable_not_derived`` per dataset variable left out, with the reason in
    ``message``. Always present; empty for an empty draft."""


class DesignSpaceValidationResponse(BaseAlbertModel):
    """Feasibility result for a design space."""

    valid: bool
    """Whether the space can produce valid formulations."""

    violations: list[DesignSpaceViolation] = Field(default_factory=list)
    """Blocking and non-blocking findings. Empty when the space is feasible."""


class DesignSpaceSample(BaseAlbertModel):
    """A preview sample of formulations drawn from a design space."""

    model_config = ConfigDict(extra="allow")


class DesignSpaceReferences(BaseAlbertModel):
    """What references a component of a design space. Powers safe removal."""

    model_config = ConfigDict(extra="allow")


class DesignSpaceApplyResponse(BaseAlbertModel):
    """The result of applying builder operations to a draft design space."""

    design_space: DesignSpace = Field(alias="designSpace")
    """The resulting design space."""

    validation: DesignSpaceValidationResponse | None = Field(default=None)
    """The feasibility check, present when one was asked for."""

    warnings: list[DesignSpaceViolation] = Field(default_factory=list)
    """Non-blocking findings. Always present; empty when there are none."""

    preview: dict[str, Any] | None = Field(default=None)
    """A sample of formulations, present when a preview was asked for."""


class _DesignSpaceOperationBase(BaseAlbertModel):
    """Base for builder operations, keeping ``op`` when serialized with unset-field exclusion.

    Operations are serialized with ``exclude_unset=True`` so that an explicit ``None``
    (for example a ``setCountBounds`` bound to clear) survives while unset fields are
    dropped. That rule would also drop the defaulted ``op`` discriminator, so it is
    re-added here.
    """

    model_config = ConfigDict(extra="forbid")

    @model_serializer(mode="wrap")
    def _keep_op_discriminator(self, handler):
        """Re-add the defaulted ``op`` field after standard serialization."""
        return {"op": self.op, **handler(self)}


class SetIngredientOperation(_DesignSpaceOperationBase):
    """Upsert an ingredient dimension, carrying its action and fraction bounds."""

    op: Literal["setIngredient"] = "setIngredient"
    """Operation kind; fixed to ``setIngredient``."""

    key: InventoryId
    """The inventory ID (format ``INV...``) of the ingredient to upsert."""

    value: IngredientEntry
    """The ingredient's action and fraction bounds."""


class ParameterAssignment(BaseAlbertModel):
    """The values a ``setParameter`` operation allows on a parameter."""

    model_config = ConfigDict(extra="forbid")

    data_type: ParameterDataType = Field(alias="dataType")
    """Whether the parameter is numeric or categorical."""

    constraint: ParameterConstraint
    """The values the parameter may take inside the space."""


class SetParameterOperation(_DesignSpaceOperationBase):
    """Upsert a parameter dimension, taking the parts of its identity as fields.

    Exactly one of ``data_template_id`` / ``parameter_group_id`` is set.
    """

    op: Literal["setParameter"] = "setParameter"
    """Operation kind; fixed to ``setParameter``."""

    parameter_id: ParameterId = Field(alias="parameterId")
    """The parameter (format ``PRM...``) to upsert."""

    data_template_id: DataTemplateId | None = Field(alias="dataTemplateId")
    """The data template (format ``DAT...``) the parameter belongs to, or ``None``."""

    parameter_group_id: ParameterGroupId | None = Field(alias="parameterGroupId")
    """The parameter group (format ``PRG...``) the parameter belongs to, or ``None``."""

    unit_id: UnitId | None = Field(alias="unitId")
    """The unit (format ``UNI...``) the parameter is expressed in, or ``None``."""

    value: ParameterAssignment
    """The parameter's data type and allowed values."""


class SetCountBoundsOperation(_DesignSpaceOperationBase):
    """Set or clear a design space's ingredient-count bounds.

    Pass ``None`` for a bound to clear it; leave a bound unset to keep it unchanged.
    """

    op: Literal["setCountBounds"] = "setCountBounds"
    """Operation kind; fixed to ``setCountBounds``."""

    min_count: int | None = Field(default=None, ge=0, alias="minCount")
    """Least ingredients in one formulation; ``None`` clears the bound."""

    max_count: int | None = Field(default=None, ge=0, alias="maxCount")
    """Most ingredients in one formulation; ``None`` clears the bound."""

    @model_validator(mode="after")
    def _at_least_one_bound(self) -> SetCountBoundsOperation:
        """Require at least one bound, since an empty operation changes nothing."""
        if not ({"min_count", "max_count"} & self.model_fields_set):
            raise ValueError(
                "SetCountBoundsOperation needs min_count or max_count "
                "(pass None to clear a bound)."
            )
        return self


class RemoveComponentOperation(_DesignSpaceOperationBase):
    """Remove an ingredient or parameter from a design space by its path."""

    op: Literal["removeComponent"] = "removeComponent"
    """Operation kind; fixed to ``removeComponent``."""

    path: str
    """Component path, ``<collection>/<key>`` (e.g. ``"ingredients/INV004"``)."""


class UpdateComponentOperation(_DesignSpaceOperationBase):
    """Change one field of a design-space component in place."""

    op: Literal["updateComponent"] = "updateComponent"
    """Operation kind; fixed to ``updateComponent``."""

    path: str
    """Component path, ``<collection>/<key>`` (e.g. ``"ingredients/INV004"``)."""

    field: str
    """The component field to change (e.g. ``"max"``)."""

    value: Any
    """The new value for the field."""


DesignSpaceOperation = Annotated[
    SetIngredientOperation
    | SetParameterOperation
    | SetCountBoundsOperation
    | RemoveComponentOperation
    | UpdateComponentOperation,
    Field(discriminator="op"),
]
"""A builder operation on a draft design space."""


class CreateDesignSpaceRequest(BaseAlbertModel):
    """The details needed to create a draft design space."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    """Display name of the design space."""

    parent_id: ProjectId = Field(alias="parentId")
    """The project (format ``PRO...``) that owns the space."""

    description: str | None = Field(default=None)
    """Free-text description of the space's intent."""

    smart_dataset_id: SmartDatasetId | None = Field(default=None, alias="smartDatasetId")
    """Smart dataset (format ``SDT...``) whose contents seed the first draft."""


class DesignSpaceForkRequest(BaseAlbertModel):
    """The details of a design-space fork."""

    model_config = ConfigDict(extra="forbid")

    parent_id: ProjectId | None = Field(default=None, alias="parentId")
    """Target project (format ``PRO...``) for the fork. ``None`` keeps the source's project."""


class DesignSpaceValidationRequest(BaseAlbertModel):
    """Optional extra context for a design-space feasibility check."""

    model_config = ConfigDict(extra="forbid")

    smart_dataset_id: SmartDatasetId | None = Field(default=None, alias="smartDatasetId")
    """Also check the space against this smart dataset (format ``SDT...``)."""

    design_model_config_id: str | None = Field(default=None, alias="designModelConfigId")
    """Also check the space against this design model config."""


class DesignSpaceSampleRequest(BaseAlbertModel):
    """The size of a design-space sample preview."""

    model_config = ConfigDict(extra="forbid")

    num_samples: int = Field(default=10, ge=1, le=25, alias="numSamples")
    """Number of formulations to draw (1 to 25)."""


class DesignSpacePreviewRequest(BaseAlbertModel):
    """A sample preview folded into an apply result."""

    model_config = ConfigDict(extra="forbid")

    num_samples: int = Field(default=10, ge=1, le=25, alias="numSamples")
    """Number of formulations to draw (1 to 25)."""


class DesignSpaceOperationsRequest(BaseAlbertModel):
    """An ordered list of builder operations to apply to a draft design space."""

    model_config = ConfigDict(extra="forbid")

    operations: list[DesignSpaceOperation] = Field(min_length=1)
    """The operations to apply, in order. Applied atomically."""

    validate_: bool = Field(default=False, alias="validate")
    """Whether to fold a feasibility check into the result."""

    preview: DesignSpacePreviewRequest | None = Field(default=None)
    """A sample preview to fold into the result."""

    dry_run: bool = Field(default=False, alias="dryRun")
    """Compute the would-be result without saving it."""
