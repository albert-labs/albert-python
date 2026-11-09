from __future__ import annotations

import sys

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
    DesignCandidateSetId,
    DesignModelConfigId,
    DesignSpaceId,
    ProjectId,
    SmartDatasetId,
    TargetId,
)
from albert.core.shared.models.base import AuditFields, BaseResource
from albert.resources.design import DesignObjective

if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
    from enum import StrEnum
else:  # pragma: no cover (py311+)
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class CandidateSetSourceType(StrEnum):
    """What produced a candidate set."""

    DESIGN_RUN = "design_run"
    MODEL_PREDICTION = "model_prediction"
    IMPORT = "import"
    MANUAL = "manual"


class CandidateSetSource(BaseAlbertModel):
    """A reference to what produced a candidate set."""

    source_type: CandidateSetSourceType = Field(alias="sourceType")
    """The kind of producer."""

    source_id: str = Field(alias="sourceId")
    """The ID of the producer, such as a design run (format ``DSR...``)."""


class DesignCandidateSet(BaseResource):
    """The candidates a design run produced. A set is read-only.

    List its candidates with
    [`get_all`][albert.collections.design_candidates.DesignCandidateCollection.get_all].
    """

    id: DesignCandidateSetId | None = Field(default=None)
    """The unique identifier of the set (format ``DCS...``)."""

    schema_version: int | None = Field(default=None, alias="schemaVersion")
    """The version of the set record layout."""

    parent_id: ProjectId | None = Field(default=None, alias="parentId")
    """The project (format ``PRO...``) that controls access to the set."""

    source: CandidateSetSource | None = Field(default=None)
    """What produced the set."""

    smart_dataset_id: SmartDatasetId | None = Field(default=None, alias="smartDatasetId")
    """The smart dataset (format ``SDT...``) the candidates were generated against."""

    design_space_id: DesignSpaceId | None = Field(default=None, alias="designSpaceId")
    """The design space (format ``DSP...``) used. ``None`` for the dataset-derived default."""

    design_model_config_id: DesignModelConfigId | None = Field(
        default=None, alias="designModelConfigId"
    )
    """The design model config (format ``DMC...``) used. ``None`` for the dataset-derived default."""

    objectives: dict[TargetId, DesignObjective] | None = Field(default=None)
    """The objectives the candidates were optimized for, keyed by target ID."""

    version: int | None = Field(default=None)
    """Version counter of the record."""

    created: AuditFields | None = Field(default=None, alias="created", frozen=True)
    """Audit fields for the creation of the set."""

    updated: AuditFields | None = Field(default=None, alias="updated", frozen=True)
    """Audit fields for the last update of the set."""
