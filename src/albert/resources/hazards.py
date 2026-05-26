from enum import Enum

from pydantic import Field

from albert.core.shared.models.base import EntityLinkWithName


class HazardSymbolStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ADDED_MANUALLY = "Added Manually"


class HazardSymbol(EntityLinkWithName):
    """Model representing a hazard symbol."""

    status: HazardSymbolStatus | None = Field(default=None)


class HazardStatement(EntityLinkWithName):
    """Model representing a hazard statement."""

    pass
