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
    """A GHS hazard pictogram symbol.

    Attributes
    ----------
    id : str
        The Albert ID of the hazard symbol.
    name : str | None
        The display name of the hazard symbol.
    status : HazardSymbolStatus | None
        Whether the symbol is active, inactive, or manually added.
    """

    status: HazardSymbolStatus | None = Field(default=None)


class HazardStatement(EntityLinkWithName):
    """A GHS hazard statement (H-statement) linked to a chemical or SDS.

    Attributes
    ----------
    id : str
        The Albert ID of the hazard statement.
    name : str | None
        The hazard statement text (e.g. ``"H301: Toxic if swallowed"``).
    """

    pass
