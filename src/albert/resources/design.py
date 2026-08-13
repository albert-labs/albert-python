from __future__ import annotations

import sys
from typing import Literal

from pydantic import Field

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


class OptimizationDesignRunRequest(BaseAlbertModel):
    """Request body for a model-guided optimization design run."""

    method: Literal[DesignMethod.GENERATE] = DesignMethod.GENERATE
    """Design-run kind; fixed to ``generate`` for optimization runs."""

    smart_dataset_id: SmartDatasetId = Field(alias="smartDatasetId")
    """Smart dataset whose experiment history anchors the run."""

    objectives: dict[TargetId, Criterion] | None = None
    """Per-target objectives; omitted to optimize every scoped target."""

    settings: OptimizationRunSettings | None = None
    """Settings for a model-guided optimization design run."""

    session: ChatSessionRef | None = None
    """Chat session to notify when the run completes; create-only."""


class DOERunSettings(BaseAlbertModel):
    """Settings for a space-filling DOE design run.

    All fields are optional; omit a field (or pass ``None``) to use the platform
    default for that knob.
    """

    num_proposals: int | None = Field(default=None, alias="numProposals", ge=1, le=100)
    """Number of space-filling proposals to generate."""

    num_samples_per_dimension: int | None = Field(
        default=None,
        alias="numSamplesPerDimension",
        ge=1,
    )
    """Samples per design-space dimension."""

    max_num_polytopes: int | None = Field(default=None, alias="maxNumPolytopes", ge=1)
    """Maximum polytopes for space-filling sampling."""

    max_num_samples: int | None = Field(default=None, alias="maxNumSamples", ge=1)
    """Maximum samples for space-filling sampling."""


class DOEDesignRunRequest(BaseAlbertModel):
    """Request body for a space-filling DOE design run."""

    method: Literal[DesignMethod.SPACE_FILLING] = DesignMethod.SPACE_FILLING
    """Design-run kind; fixed to ``space_filling`` for DOE runs."""

    smart_dataset_id: SmartDatasetId = Field(alias="smartDatasetId")
    """Smart dataset whose experiment history anchors the run."""

    anchor_targets: list[TargetId] | None = Field(default=None, alias="anchorTargets")
    """Target ids that narrow which existing rows count as historical anchors."""

    settings: DOERunSettings | None = None
    """Settings for a space-filling DOE design run."""

    session: ChatSessionRef | None = None
    """Chat session to notify when the run completes; create-only."""
