from __future__ import annotations

import sys
from datetime import datetime
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
    DesignModelConfigId,
    ProjectId,
    SmartDatasetId,
    TargetId,
)
from albert.core.shared.models.base import AuditFields, BaseResource
from albert.resources.design_operands import (
    IngredientAmountOperand,
    LabelFractionOperand,
    ParameterOperand,
    PropertyAggregationOperand,
    QuantityOperand,
    TypedDesignModel,
)
from albert.resources.design_spaces import (
    RemoveComponentOperation,
    UpdateComponentOperation,
    _DesignSpaceOperationBase,
)

if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
    from enum import StrEnum
else:  # pragma: no cover (py311+)
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class DesignModelConfigState(StrEnum):
    """Lifecycle of a design model config. Orthogonal to its soft-delete ``status``."""

    DRAFT = "draft"
    PUBLISHED = "published"


class OutputDataType(StrEnum):
    """The kind of prediction task an output is."""

    NUMERIC = "numeric"
    CATEGORICAL = "categorical"


class OutputTransform(StrEnum):
    """A transform applied to a numeric output before modelling."""

    NONE = "none"
    LOG = "log"
    ASINH = "asinh"
    YEO_JOHNSON = "yeoJohnson"
    BOX_COX = "boxCox"


class FeatureFamily(StrEnum):
    """The default feature families a resolved feature belongs to."""

    INGREDIENT_AMOUNT = "ingredient_amount"
    LABEL_FRACTION = "label_fraction"
    INGREDIENT_PROPERTY = "ingredient_property"
    PARAMETER = "parameter"


class DesignModelConfigViolationCode(StrEnum):
    """Machine-readable category of a design model config finding."""

    TARGET_NOT_IN_DATASET = "target_not_in_dataset"
    TRANSFORM_REQUIRES_POSITIVE_TARGET = "transform_requires_positive_target"
    INERT_MASK_ENTRY = "inert_mask_entry"
    FEATURE_DROPPED_BY_OVERLAP = "feature_dropped_by_overlap"
    ESTIMATOR_DOWNGRADED = "estimator_downgraded"
    UNKNOWN_REFERENCE = "unknown_reference"
    DIMENSION_NOT_MODELLED = "dimension_not_modelled"
    INVALID_SETTINGS = "invalid_settings"
    INVALID_CONSTRAINT = "invalid_constraint"
    VARIABLE_NOT_DERIVED = "variable_not_derived"


class FamilySelector(TypedDesignModel):
    """A mask entry matching every default feature of one family."""

    type: Literal[
        "allIngredientAmounts",
        "allLabelFractions",
        "allIngredientProperties",
        "allParameters",
    ]
    """Which family to match: all ingredient amounts, label fractions, ingredient
    property aggregations, or parameters."""


MaskEntry = Annotated[
    FamilySelector
    | IngredientAmountOperand
    | LabelFractionOperand
    | ParameterOperand
    | PropertyAggregationOperand,
    Field(discriminator="type"),
]
"""One feature-mask entry: a family selector or a quantity descriptor."""


class FeatureMask(BaseAlbertModel):
    """Which features an output uses: exactly one of ``include`` or ``exclude``.

    Each is a non-empty list of mask entries. An output with no mask uses all features.
    """

    model_config = ConfigDict(extra="forbid")

    include: list[MaskEntry] | None = Field(default=None, min_length=1)
    """Use only the features these entries match."""

    exclude: list[MaskEntry] | None = Field(default=None, min_length=1)
    """Use every feature except those these entries match."""

    @model_validator(mode="after")
    def _exactly_one_list(self) -> FeatureMask:
        """Require exactly one of ``include`` / ``exclude``."""
        if (self.include is None) == (self.exclude is None):
            raise ValueError("Exactly one of include / exclude must be set.")
        return self


class OutputEntry(BaseAlbertModel):
    """One predicted target's wiring, keyed by target ID in a config's ``outputs``.

    Fields the SDK does not model (for example beta ones) are kept as extra fields and
    sent back unchanged.
    """

    model_config = ConfigDict(extra="allow")

    data_type: OutputDataType = Field(alias="dataType")
    """Whether the target is numeric or categorical."""

    output_transform: OutputTransform | None = Field(default=None, alias="outputTransform")
    """Transform for a numeric output. A transform other than ``none`` on a categorical
    output is rejected when applied (``invalid_settings``). Omit for no transform."""

    features: FeatureMask | None = Field(default=None)
    """Which features this output uses. Omit to use all features."""


class DesignModelConfig(BaseResource):
    """A design model config: which targets to predict, how to transform them, and which
    default features each one uses.

    A config is created as a draft, edited with builder operations, checked against a
    smart dataset, and published. A published config is frozen; editing one means
    forking it into a new draft.
    """

    id: DesignModelConfigId | None = Field(default=None)
    """The unique identifier of the config (format ``DMC...``)."""

    schema_version: int | None = Field(default=None, alias="schemaVersion")
    """Pins the default feature-set definition. Not a concurrency counter."""

    name: str | None = Field(default=None, min_length=1)
    """Display name of the config."""

    description: str | None = Field(default=None)
    """Free-text description of the config's intent."""

    parent_id: ProjectId | None = Field(default=None, alias="parentId")
    """The project (format ``PRO...``) that owns the config and controls access to it."""

    state: DesignModelConfigState | None = Field(default=None)
    """Lifecycle state: ``draft`` (editable) or ``published`` (frozen)."""

    published_at: datetime | None = Field(default=None, alias="publishedAt")
    """When the config was published; ``None`` while it is a draft."""

    forked_from_id: DesignModelConfigId | None = Field(default=None, alias="forkedFromId")
    """The published config this draft was forked from, if any."""

    derived_from_id: SmartDatasetId | None = Field(default=None, alias="derivedFromId")
    """The smart dataset (format ``SDT...``) that seeded the first draft, if any.
    Provenance only; the config does not track the dataset afterwards."""

    outputs: dict[TargetId, OutputEntry] | None = Field(default=None)
    """Output wiring, keyed by target ID (format ``TAR...``). Empty when absent."""

    version: int | None = Field(default=None)
    """Optimistic-concurrency counter, checked on every write."""

    created: AuditFields | None = Field(default=None, alias="created", frozen=True)
    """Audit fields for the creation of the config."""

    updated: AuditFields | None = Field(default=None, alias="updated", frozen=True)
    """Audit fields for the last update of the config."""


class DesignModelConfigViolation(BaseAlbertModel):
    """A single design model config finding."""

    code: DesignModelConfigViolationCode
    """Machine-readable category of the finding."""

    message: str
    """Human-readable explanation of the finding."""

    target_id: str | None = Field(default=None, alias="targetId")
    """The target the finding is scoped to, when applicable."""

    components: list[str] | None = Field(default=None)
    """Component paths (``<collection>/<key>``) the finding is attributed to."""

    op_index: int | None = Field(default=None, alias="opIndex")
    """Position, in the ``operations`` passed to ``apply``, of the operation behind the finding.

    ``None`` when the finding is not tied to an operation.
    """


class DesignModelConfigCreated(DesignModelConfig):
    """A newly created draft config, with any findings from seeding it."""

    warnings: list[DesignModelConfigViolation] = Field(default_factory=list)
    """Non-blocking findings. Always present; empty when there are none."""


class DesignModelConfigValidationResponse(BaseAlbertModel):
    """The result of checking a design model config."""

    valid: bool
    """Whether the config passed. ``False`` is a normal result, not an error."""

    violations: list[DesignModelConfigViolation] = Field(default_factory=list)
    """Blocking and non-blocking findings. Empty when the config is valid."""


class ResolvedFeature(BaseAlbertModel):
    """One concrete feature of a resolved feature set."""

    model_config = ConfigDict(extra="allow")

    key: str
    """Stable feature key, the feature's identity across resolutions. Keys have the form
    ``ingredient/<INV id>``, ``label/<tag or local key>``,
    ``property/<mean|sum>/<name>[/<label>]``, ``parameter/<composite key>`` or
    ``parameter/<composite key>/<category>``. Treat a key as opaque."""

    family: FeatureFamily
    """The default family the feature belongs to."""

    descriptor: QuantityOperand
    """The quantity the feature computes."""

    value: str | None = Field(default=None)
    """The category a one-hot parameter feature encodes; ``None`` otherwise."""

    origin: str = Field(default="default")
    """``default`` for the always-computed default set; otherwise the key of the extra
    feature that authored it."""


class DesignModelConfigResolvedFeatures(BaseAlbertModel):
    """The features a config resolves to against a smart dataset, and how outputs use them."""

    model_config = ConfigDict(extra="allow")

    features: list[ResolvedFeature] = Field(default_factory=list)
    """The full resolved set in a deterministic order, before any output mask."""

    outputs: dict[str, list[str]] = Field(default_factory=dict)
    """Target ID to the keys of the features its mask routes, in feature order."""

    warnings: list[DesignModelConfigViolation] = Field(default_factory=list)
    """Non-blocking findings. Empty when there are none."""


class FeaturePreviewRowIdentifiers(BaseAlbertModel):
    """The Albert records a featurized row was measured on."""

    model_config = ConfigDict(extra="allow")

    type: Literal["albert_measurement"] = "albert_measurement"
    """The identifier kind. Preview rows are always single measurements."""

    inventory_id: str = Field(alias="inventoryId")
    """The formula or inventory item the row was measured on."""

    lot_id: str | None = Field(default=None, alias="lotId")
    """The lot, when the measurement is on a lot."""

    workflow_interval: str = Field(alias="workflowInterval")
    """The workflow interval of the measurement."""

    task_id: str | None = Field(default=None, alias="taskId")
    """The task that recorded the measurement."""

    property_data_id: str = Field(alias="propertyDataId")
    """The property data record."""

    project_id: str | None = Field(default=None, alias="projectId")
    """Derived from ``inventory_id`` during the dataset build (temporary). Link records with
    ``inventory_id`` and ``lot_id`` instead."""


class FeaturePreviewRow(BaseAlbertModel):
    """One featurized experiment row."""

    model_config = ConfigDict(extra="allow")

    experiment_id: str = Field(alias="experimentId")
    """The experiment's row key in the dataset. Opaque; use ``identifiers`` to link the row to
    Albert records."""

    identifiers: FeaturePreviewRowIdentifiers | None = None
    """The Albert records the row was measured on. ``None`` when the dataset's rows carry no
    Albert identifiers."""

    values: dict[str, float | int | bool | str | None] = Field(default_factory=dict)
    """Stable feature key to value. Missing values (NaN) are ``None``."""


class FeatureSummary(BaseAlbertModel):
    """A per-feature summary over the previewed rows."""

    model_config = ConfigDict(extra="allow")

    key: str
    """Stable feature key."""

    dtype: str
    """Dtype of the featurized column."""

    nan_count: int = Field(alias="nanCount")
    """Previewed rows where the feature is missing."""

    constant: bool
    """Whether the feature has at most one distinct non-missing value across the rows."""


class AutomaticFeatures(BaseAlbertModel):
    """Features computed automatically, without a stable key (for example molecular
    descriptors). They are always used, cannot be masked, and are not in the row values."""

    model_config = ConfigDict(extra="allow")

    count: int
    """How many automatic features there are."""

    names: list[str] = Field(default_factory=list)
    """Their names."""


class DesignModelConfigFeaturePreview(BaseAlbertModel):
    """The first few dataset rows run through a config's resolved features, with no model fit."""

    model_config = ConfigDict(extra="allow")

    num_rows: int = Field(alias="numRows")
    """Rows previewed, after the server clamped the request."""

    rows: list[FeaturePreviewRow] = Field(default_factory=list)
    """The featurized rows. Values are limited to the first keyed feature columns."""

    columns_truncated: bool = Field(default=False, alias="columnsTruncated")
    """Whether ``rows`` carry fewer features than ``summary``."""

    summary: list[FeatureSummary] = Field(default_factory=list)
    """Every keyed feature, in feature order."""

    automatic_features: AutomaticFeatures = Field(alias="automaticFeatures")
    """The unkeyed features that are always used."""

    warnings: list[DesignModelConfigViolation] = Field(default_factory=list)
    """Non-blocking findings. Empty when there are none."""


class DesignModelConfigReferences(BaseAlbertModel):
    """What references a component of a design model config. Powers safe removal."""

    model_config = ConfigDict(extra="allow")


class DesignModelConfigApplyResponse(BaseAlbertModel):
    """The result of applying builder operations to a draft design model config."""

    design_model_config: DesignModelConfig = Field(alias="modelConfig")
    """The resulting design model config. The wire field is ``modelConfig``; it is named
    differently here because ``model_config`` is reserved by the model base class."""

    validation: DesignModelConfigValidationResponse | None = Field(default=None)
    """The check result, present when one was asked for."""

    preview: DesignModelConfigFeaturePreview | None = Field(default=None)
    """The feature preview, present when one was asked for."""

    resolved_features: DesignModelConfigResolvedFeatures | None = Field(
        default=None, alias="resolvedFeatures"
    )
    """The resolved features, present when they were asked for."""

    warnings: list[DesignModelConfigViolation] = Field(default_factory=list)
    """Non-blocking findings. Empty when there are none."""


class SetOutputOperation(_DesignSpaceOperationBase):
    """Upsert one target's whole wiring."""

    op: Literal["setOutput"] = "setOutput"
    """Operation kind; fixed to ``setOutput``."""

    key: TargetId
    """The target ID (format ``TAR...``) to upsert."""

    value: OutputEntry
    """The target's full wiring: data type, transform and feature mask."""


DesignModelConfigOperation = Annotated[
    SetOutputOperation | RemoveComponentOperation | UpdateComponentOperation,
    Field(discriminator="op"),
]
"""A builder operation on a draft design model config.

``RemoveComponentOperation`` and ``UpdateComponentOperation`` are the same classes
design spaces use; here the path is ``outputs/<target id>``.
"""


class CreateDesignModelConfigRequest(BaseAlbertModel):
    """The details needed to create a draft design model config."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    """Display name of the config."""

    parent_id: ProjectId = Field(alias="parentId")
    """The project (format ``PRO...``) that owns the config."""

    description: str | None = Field(default=None)
    """Free-text description of the config's intent."""

    smart_dataset_id: SmartDatasetId | None = Field(default=None, alias="smartDatasetId")
    """Smart dataset (format ``SDT...``) to derive the first draft from."""


class DesignModelConfigForkRequest(BaseAlbertModel):
    """The details of a design model config fork."""

    model_config = ConfigDict(extra="forbid")

    parent_id: ProjectId | None = Field(default=None, alias="parentId")
    """Target project (format ``PRO...``) for the fork. ``None`` keeps the source's project."""


class DesignModelConfigValidationRequest(BaseAlbertModel):
    """The dataset to check a design model config against."""

    model_config = ConfigDict(extra="forbid")

    smart_dataset_id: SmartDatasetId = Field(alias="smartDatasetId")
    """Smart dataset (format ``SDT...``) to check against."""


class DesignModelConfigPreviewRequest(BaseAlbertModel):
    """A feature preview folded into an apply result."""

    model_config = ConfigDict(extra="forbid")

    num_rows: int = Field(alias="numRows")
    """Rows to preview. The server clamps it to 1..25."""


class DesignModelConfigOperationsRequest(BaseAlbertModel):
    """An ordered list of builder operations to apply to a draft design model config."""

    model_config = ConfigDict(extra="forbid")

    operations: list[DesignModelConfigOperation] = Field(min_length=1)
    """The operations to apply, in order. Applied atomically."""

    validate_: bool = Field(default=False, alias="validate")
    """Whether to fold a check into the result."""

    preview: DesignModelConfigPreviewRequest | None = Field(default=None)
    """A feature preview to fold into the result. Needs ``smart_dataset_id``."""

    resolve: bool = Field(default=False)
    """Whether to fold the resolved features into the result. Needs ``smart_dataset_id``."""

    dry_run: bool = Field(default=False, alias="dryRun")
    """Compute the would-be result without saving it."""

    smart_dataset_id: SmartDatasetId | None = Field(default=None, alias="smartDatasetId")
    """Smart dataset (format ``SDT...``) for the folded checks."""
