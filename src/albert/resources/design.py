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
