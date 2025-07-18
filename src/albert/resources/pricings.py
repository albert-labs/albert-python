from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import InventoryId
from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import SerializeAsEntityLink
from albert.resources.companies import Company
from albert.resources.locations import Location


class LeadTimeUnit(str, Enum):
    """The unit of measure for the provided lead time."""

    DAYS = "Days"
    WEEKS = "Weeks"
    MONTHS = "Months"


class Pricing(BaseResource):
    """A Price of a given InventoryItem at a given Location.

    Attributes
    ----------
    id : str | None
        The Albert ID of the pricing. Set when the pricing is retrieved from Albert.
    inventory_id : str
        The Albert ID of the inventory item.
    company : Company
        The company that the pricing belongs to.
    location : Location
        The location that the pricing belongs to.
    description : str | None
        The description of the pricing. Optional.
    pack_size : str | None
        The pack size of the pricing. Optional. Used to calculate the cost per unit.
    price : float
        The price of the pricing IN CURRENCY/ KG or CURRENCY/L! Must do the conversion! Depends on InventoryItem's unit of measure.
    currency : str
        The currency of the pricing. Defaults to `USD`.
    fob : str | None
        The FOB of the pricing. Optional.
    lead_time : int | None
        The lead time of the pricing. Optional.
    lead_time_unit : LeadTimeUnit | None
        The unit of measure for the provided lead time. Optional.
    expiration_date : str | None
        The expiration date of the pricing. YYYY-MM-DD format.
    """

    id: str | None = Field(default=None, alias="albertId")
    inventory_id: str | None = Field(default=None, alias="parentId")
    company: SerializeAsEntityLink[Company] = Field(alias="Company")
    location: SerializeAsEntityLink[Location] = Field(alias="Location")
    description: str | None = Field(default=None)
    pack_size: str | None = Field(default=None, alias="packSize")
    price: float = Field(ge=0, le=9999999999)
    currency: str = Field(default="USD", alias="currency")
    fob: str | None = Field(default=None)
    lead_time: int | None = Field(default=None, alias="leadTime")
    lead_time_unit: LeadTimeUnit | None = Field(default=None, alias="leadTimeUnit")
    expiration_date: str | None = Field(default=None, alias="expirationDate")

    # Read-only fields
    default: int | None = Field(default=None, exclude=True, frozen=True)


class InventoryPricings(BaseAlbertModel):
    """Pricings for a given InventoryItem.

    Attributes
    ----------
    inventory_id : Inventory
        The inventory ID the pricings belong to.
    pricings : list[Pricing]
        The list of pricings.
    """

    inventory_id: InventoryId = Field(..., alias="id")
    pricings: list[Pricing]


class PricingBy(str, Enum):
    LOCATION = "Location"
    COMPANY = "Company"
