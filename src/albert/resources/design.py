from __future__ import annotations

import sys
from typing import Literal

from pydantic import Field, field_validator, model_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import SmartDatasetId, TargetId
from albert.resources.chats import ChatSessionRef
from albert.resources.targets import Criterion

if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
    from enum import StrEnum
else:  # pragma: no cover (py311+)
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class DesignMethod(StrEnum):
    """Wire ``method`` value for a design-run request."""

    GENERATE = "generate"
    SPACE_FILLING = "space_filling"


class DesignRunViolationCode(StrEnum):
    """Structured preflight failure codes returned by design-run validation."""

    INVALID_SETTINGS = "invalid_settings"
    DATASET_NOT_READY = "dataset_not_ready"
    OBJECTIVE_OUT_OF_SCOPE = "objective_out_of_scope"
    NO_PERFORMANCE_TARGETS = "no_performance_targets"
    INVALID_OBJECTIVE = "invalid_objective"
    INSUFFICIENT_TRAINING_DATA = "insufficient_training_data"
    INFEASIBLE_DESIGN_SPACE = "infeasible_design_space"
    MODEL_TRAINING_ERROR = "model_training_error"
    OPTIMIZATION_SYSTEM_MISMATCH = "optimization_system_mismatch"
    INTERNAL = "internal"
    JOB_TIMEOUT = "job_timeout"


class DesignRunViolation(BaseAlbertModel):
    """A single validation failure for a design-run configuration."""

    code: DesignRunViolationCode
    """Machine-readable violation category."""

    message: str
    """Human-readable explanation of the failure."""

    target_id: str | None = Field(default=None, alias="targetId")
    """Target id when the violation is scoped to one performance target."""


class DesignRunValidationResponse(BaseAlbertModel):
    """Preflight result for a design-run configuration."""

    valid: bool
    """Whether the configuration passed validation."""

    violations: list[DesignRunViolation] = Field(default_factory=list)
    """Structured failures when ``valid`` is ``False``."""

    target_sample_counts: dict[str, int] | None = Field(default=None, alias="targetSampleCounts")
    """Non-null measurement count per performance target in the dataset scope."""


class OptimizationRunSettings(BaseAlbertModel):
    """Settings for a model-guided optimization design run.

    All fields are optional; omit a field (or pass ``None``) to use the platform
    default for that knob. Values outside the allowed ranges are rejected before
    the run is submitted.

    Notes
    -----
    These two settings work together: candidate generation produces up to
    ``num_candidates_generated`` candidates, then the top ``num_candidates_selected``
    diverse formulations are kept as the result batch.
    """

    num_candidates_generated: int | None = Field(default=None, alias="numCandidatesGenerated")
    """Total candidates to generate before diversity selection (default ``100000``, range ``1``–``100000``)."""

    num_candidates_selected: int | None = Field(default=None, alias="numCandidatesSelected")
    """Top diverse candidates to return after ranking (default ``20``, range ``1``–``100``)."""


class DesignObjective(Criterion):
    """A per-run optimization goal: a success criterion plus how much it matters.

    A [`Criterion`][albert.resources.targets.Criterion] states what good looks like.
    ``weight`` states how much that goal counts relative to the other objectives on the
    same run, and belongs to the run rather than to the Target. A Target carries no
    priority of its own, so the same targets can be reweighted from one run to the next
    to see how the trade-off moves the candidates.

    A plain ``Criterion`` is accepted anywhere a ``DesignObjective`` is expected and
    takes the default weight.

    !!! example
        ```python
        from albert.resources.design import DesignObjective

        # a hard specification that should not be traded away
        DesignObjective(operator="gte", value=95, weight=3.0)

        # the same goal at the default weight
        DesignObjective(operator="gte", value=95)
        ```
    """

    weight: float = Field(default=1.0, gt=0)
    """How much this objective counts relative to the others on the same run.

    Candidate scores are combined as a product of each objective's score raised to its
    weight, so a weight above ``1.0`` makes the objective harder to trade away and a
    weight below ``1.0`` makes it easier. Must be positive; to ignore an objective,
    leave it out.

    Always a float, never ``None``: an unweighted objective is ``1.0``, which weighs it
    equally against the others. Omitting the field, or passing an explicit ``None``,
    both give ``1.0``.
    """

    @model_validator(mode="before")
    @classmethod
    def _accept_plain_criterion(cls, value: object) -> object:
        """Accept a plain Criterion, giving it the default weight."""
        if isinstance(value, Criterion) and not isinstance(value, cls):
            return value.model_dump()
        return value

    @field_validator("weight", mode="before")
    @classmethod
    def _null_weight_is_unweighted(cls, value: object) -> object:
        """Treat an explicit null as unset, so the weight is always a float."""
        return 1.0 if value is None else value


class OptimizationDesignRunRequest(BaseAlbertModel):
    """Request body for a model-guided optimization design run."""

    method: Literal[DesignMethod.GENERATE] = DesignMethod.GENERATE
    """Design-run kind; fixed to ``generate`` for optimization runs."""

    smart_dataset_id: SmartDatasetId = Field(alias="smartDatasetId")
    """Smart dataset whose experiment history anchors the run."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    """Display name for the resulting insight; a name is generated when omitted."""

    objectives: dict[TargetId, DesignObjective] | None = None
    """Per-target objectives, each with its weight; omitted to optimize every scoped target."""

    settings: OptimizationRunSettings | None = None
    """Settings for a model-guided optimization design run."""

    session: ChatSessionRef | None = None
    """Chat session to notify when the run completes; create-only."""


class DOERunSettings(BaseAlbertModel):
    """Settings for a space-filling DOE design run.

    All fields are optional; omit a field (or pass ``None``) to use the platform
    default for that knob. Values outside the allowed ranges are rejected before
    the run is submitted.

    Notes
    -----
    These two settings work together: up to ``num_candidates_generated`` candidates
    are sampled from the design space, then a space-filling subset of size
    ``num_candidates_selected`` is returned.
    """

    num_candidates_generated: int | None = Field(default=None, alias="numCandidatesGenerated")
    """Maximum candidates to sample before downsampling (default ``10000``, range ``1``–unbounded)."""

    num_candidates_selected: int | None = Field(default=None, alias="numCandidatesSelected")
    """Size of the space-filling subset returned (default ``20``, range ``1``–``100``)."""


class DOEDesignRunRequest(BaseAlbertModel):
    """Request body for a space-filling DOE design run."""

    method: Literal[DesignMethod.SPACE_FILLING] = DesignMethod.SPACE_FILLING
    """Design-run kind; fixed to ``space_filling`` for DOE runs."""

    smart_dataset_id: SmartDatasetId = Field(alias="smartDatasetId")
    """Smart dataset whose experiment history anchors the run."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    """Display name for the resulting insight; a name is generated when omitted."""

    anchor_targets: list[TargetId] | None = Field(default=None, alias="anchorTargets")
    """Target ids that narrow which existing rows count as historical anchors."""

    settings: DOERunSettings | None = None
    """Settings for a space-filling DOE design run."""

    session: ChatSessionRef | None = None
    """Chat session to notify when the run completes; create-only."""
