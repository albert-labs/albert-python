from __future__ import annotations

import sys
from typing import Annotated

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import (
    DesignCandidateId,
    DesignCandidateSetId,
    ProjectId,
    TargetId,
)
from albert.core.shared.models.base import AuditFields, BaseResource
from albert.resources.design_operands import IngredientAmountOperand, ParameterOperand
from albert.resources.design_spaces import ParameterRef

if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
    from enum import StrEnum
else:  # pragma: no cover (py311+)
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class PredictionDataType(StrEnum):
    """The kind of prediction a model made for a target."""

    NUMERIC = "numeric"
    CATEGORICAL = "categorical"


class IngredientAmountInput(IngredientAmountOperand):
    """The sampled amount of one ingredient."""

    value: float
    """The sampled amount."""


class ParameterInput(ParameterOperand):
    """The sampled value of one parameter."""

    ref: ParameterRef
    """The structured parts of the parameter key."""

    value: float | str
    """The sampled value."""


CandidateInput = Annotated[IngredientAmountInput | ParameterInput, Field(discriminator="type")]
"""One sampled design variable: an ingredient amount or a parameter value."""


class Quantiles(BaseAlbertModel):
    """The full predicted distribution of a numeric prediction."""

    levels: list[float]
    """The quantile levels."""

    values: list[float]
    """The predicted value at each level."""


class Prediction(BaseAlbertModel):
    """A model's prediction for one target."""

    value: float | str
    """The predicted value."""

    uncertainty: float
    """The uncertainty of the prediction."""

    data_type: PredictionDataType = Field(alias="dataType")
    """Whether the prediction is ``numeric`` or ``categorical``."""

    quantiles: Quantiles | None = Field(default=None)
    """The predicted distribution. Numeric predictions only."""


class Acquisition(BaseAlbertModel):
    """How well a candidate scored against the run's objectives."""

    score: float
    """The overall score."""

    per_objective: dict[str, float] | None = Field(default=None, alias="perObjective")
    """Raw, unweighted score per objective, keyed by target ID."""


class DesignCandidate(BaseResource):
    """One candidate formulation of a candidate set. Candidates are read-only."""

    id: DesignCandidateId | None = Field(default=None)
    """The unique identifier of the candidate (format ``DCN...``)."""

    schema_version: int | None = Field(default=None, alias="schemaVersion")
    """The version of the candidate record layout."""

    candidate_set_id: DesignCandidateSetId | None = Field(default=None, alias="candidateSetId")
    """The candidate set (format ``DCS...``) the candidate belongs to."""

    parent_id: ProjectId | None = Field(default=None, alias="parentId")
    """The project (format ``PRO...``) that controls access to the candidate."""

    inputs: list[CandidateInput] = Field(default_factory=list)
    """Every sampled design variable, zero values included."""

    predictions: dict[TargetId, Prediction] | None = Field(default=None)
    """Predictions keyed by target ID. Absent on space-filling candidates."""

    acquisition: Acquisition | None = Field(default=None)
    """The candidate's score. Absent when nothing scored it."""

    rank: int | None = Field(default=None)
    """Position within the set by descending acquisition score, starting at 1.

    Only returned when listing candidates, and only for scored sets; ``None`` from a
    single-candidate read."""

    version: int | None = Field(default=None)
    """Version counter of the record."""

    created: AuditFields | None = Field(default=None, alias="created", frozen=True)
    """Audit fields for the creation of the candidate."""

    updated: AuditFields | None = Field(default=None, alias="updated", frozen=True)
    """Audit fields for the last update of the candidate."""
