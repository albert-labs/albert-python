from enum import Enum

from pydantic import Field

from albert.core.shared.models.base import EntityLinkWithName


class HazardSymbolStatus(str, Enum):
    """The status of a :class:`HazardSymbol`.

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
    """A GHS hazard pictogram symbol from the platform reference list.

    Returned by
    :meth:`~albert.collections.hazards.HazardsCollection.get_symbols`.

    Attributes
    ----------
    id : str
        The Albert ID of the hazard symbol.
    name : str | None
        The display name of the hazard symbol.
    category : str | None
        The category of the hazard symbol, when set.
    status : HazardSymbolStatus | None
        Whether the symbol is active, inactive, or was added manually.
    """

    status: HazardSymbolStatus | None = Field(default=None)


class HazardStatement(EntityLinkWithName):
    """A GHS hazard statement from the platform reference list.

    Returned by
    :meth:`~albert.collections.hazards.HazardsCollection.get_statements`.

    Attributes
    ----------
    id : str
        The Albert ID of the hazard statement.
    name : str | None
        The text of the hazard statement.
    category : str | None
        The category of the hazard statement, when set.
    """

    pass
