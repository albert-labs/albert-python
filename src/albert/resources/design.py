from enum import StrEnum

from pydantic import Field

from albert.core.base import BaseAlbertModel


class DesignMethod(StrEnum):
    """Type of inverse-design run to create."""

    GENERATE = "generate"


class DesignRunSettings(BaseAlbertModel):
    """Optional run sizing for an inverse-design generate run.

    All fields are optional; omit a field (or pass ``None``) to use the platform
    default for that knob. Values outside the allowed ranges are rejected before
    the run is submitted.

    Attributes
    ----------
    num_candidates_generated : int | None
        Total number of candidates to generate before diversity selection narrows
        them down. Default: ``100000``. Allowed range: ``1``–``100000``.
    num_candidates_selected : int | None
        Number of diverse candidates to return after ranking and selecting from
        the generated candidates. Default: ``20``. Allowed range: ``1``–``100``.

    Notes
    -----
    These two settings work together: candidate generation produces up to
    ``num_candidates_generated`` candidates, then the top ``num_candidates_selected``
    diverse formulations are kept as the result batch.
    """

    num_candidates_generated: int | None = Field(default=None, alias="numCandidatesGenerated")
    num_candidates_selected: int | None = Field(default=None, alias="numCandidatesSelected")
