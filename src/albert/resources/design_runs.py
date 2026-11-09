from __future__ import annotations

import sys
from datetime import datetime

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
    DesignCandidateSetId,
    DesignModelConfigId,
    DesignRunId,
    DesignSpaceId,
    ProjectId,
    SmartDatasetId,
    TargetId,
)
from albert.core.shared.models.base import AuditFields, BaseResource
from albert.resources.design import DesignMethod, DesignObjective, DesignRunViolation

if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
    from enum import StrEnum
else:  # pragma: no cover (py311+)
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class DesignRunState(StrEnum):
    """Lifecycle of a design run. Orthogonal to its soft-delete ``status``."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


class DesignRunStage(StrEnum):
    """Detail on what a ``running`` run is doing."""

    BUILDING_MODELS = "building_models"
    GENERATING_CANDIDATES = "generating_candidates"
    SAMPLING = "sampling"


class DesignRunSettings(BaseAlbertModel):
    """The sizing a design run was triggered with."""

    num_candidates_generated: int | None = Field(default=None, alias="numCandidatesGenerated")
    """Candidates generated before selection (optimization) or the most sampled before
    downsampling (space-filling)."""

    num_candidates_selected: int | None = Field(default=None, alias="numCandidatesSelected")
    """Candidates kept (at most ``100``)."""


class DesignRun(BaseResource):
    """A stored design run and its status.

    Once ``state`` is ``complete``, ``result_set_id`` names the candidate set holding
    its candidates; read it with
    [`DesignCandidateSetCollection`][albert.collections.design_candidate_sets.DesignCandidateSetCollection].
    """

    id: DesignRunId | None = Field(default=None)
    """The unique identifier of the run (format ``DSR...``)."""

    schema_version: int | None = Field(default=None, alias="schemaVersion")
    """The version of the run record layout."""

    name: str | None = Field(default=None, min_length=1)
    """Display name of the run."""

    description: str | None = Field(default=None)
    """Free-text description of the run."""

    parent_id: ProjectId | None = Field(default=None, alias="parentId")
    """The project (format ``PRO...``) that owns the run and controls access to it."""

    method: DesignMethod | None = Field(default=None)
    """How candidates are produced: ``generate`` or ``space_filling``."""

    state: DesignRunState | str | None = Field(default=None, union_mode="left_to_right")
    """Lifecycle state: ``queued``, ``running``, ``complete`` or ``error``. A state this
    version does not know yet is kept as a plain string."""

    stage: DesignRunStage | str | None = Field(default=None, union_mode="left_to_right")
    """What the run is doing while ``running``. A stage this version does not know yet is
    kept as a plain string."""

    violations: list[DesignRunViolation] | None = Field(default=None)
    """Why the run failed. Populated when ``state`` is ``error``."""

    started_at: datetime | None = Field(default=None, alias="startedAt")
    """When the run started."""

    ended_at: datetime | None = Field(default=None, alias="endedAt")
    """When the run reached a terminal state."""

    smart_dataset_id: SmartDatasetId | None = Field(default=None, alias="smartDatasetId")
    """The smart dataset (format ``SDT...``) the run was triggered against."""

    design_space_id: DesignSpaceId | None = Field(default=None, alias="designSpaceId")
    """The design space (format ``DSP...``) used. ``None`` for the dataset-derived default."""

    design_model_config_id: DesignModelConfigId | None = Field(
        default=None, alias="designModelConfigId"
    )
    """The design model config (format ``DMC...``) used. ``None`` for the dataset-derived default."""

    objectives: dict[TargetId, DesignObjective] | None = Field(default=None)
    """Per-target objectives, keyed by target ID. Optimization runs only."""

    anchor_targets: list[TargetId] | None = Field(default=None, alias="anchorTargets")
    """Target IDs that narrowed which experiments anchor a space-filling run."""

    settings: DesignRunSettings | None = Field(default=None)
    """The sizing the run was triggered with."""

    result_set_id: DesignCandidateSetId | None = Field(default=None, alias="resultSetId")
    """The candidate set (format ``DCS...``) of the run's candidates. ``None`` until the run
    is ``complete``."""

    version: int | None = Field(default=None)
    """Version counter of the record."""

    created: AuditFields | None = Field(default=None, alias="created", frozen=True)
    """Audit fields for the creation of the run."""

    updated: AuditFields | None = Field(default=None, alias="updated", frozen=True)
    """Audit fields for the last update of the run."""
