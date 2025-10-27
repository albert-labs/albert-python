from pydantic import Field

from albert.core.shared.enums import Status
from albert.core.shared.models.base import EntityLinkWithName


class HazardSymbol(EntityLinkWithName):
    """Model representing a hazard symbol."""

    status: Status | None = Field(default=None)


class HazardStatement(EntityLinkWithName):
    """Model representing a hazard statement."""

    pass
