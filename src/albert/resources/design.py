import sys

from pydantic import Field

from albert.core.base import BaseAlbertModel

if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
    from enum import StrEnum
else:  # pragma: no cover (py311+)
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class DesignMethod(StrEnum):
    """The kind of inverse-design run to create."""

    GENERATE = "generate"


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


class DesignRunSettings(BaseAlbertModel):
    """Optional run sizing for an inverse-design generate run.

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
