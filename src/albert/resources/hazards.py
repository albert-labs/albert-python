from enum import Enum

from pydantic import Field

from albert.core.shared.models.base import EntityLinkWithName


class HazardSymbolStatus(str, Enum):
    """The status of a HazardSymbol.

    Attributes
    ----------
    ACTIVE : str
        The hazard symbol is fully operational and visible in normal operations.
    INACTIVE : str
        The hazard symbol is hidden from normal operations and disabled from use.
    ADDED_MANUALLY : str
        The hazard symbol was manually chosen.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    ADDED_MANUALLY = "Added Manually"


class HazardSymbol(EntityLinkWithName):
    """Model representing a hazard symbol."""

    status: HazardSymbolStatus | None = Field(default=None)


class HazardStatement(EntityLinkWithName):
    """Model representing a hazard statement."""

    pass
