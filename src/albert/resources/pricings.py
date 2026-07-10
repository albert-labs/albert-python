from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import InventoryId
from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import SerializeAsEntityLink
from albert.resources.companies import Company
from albert.resources.locations import Location


class LeadTimeUnit(str, Enum):
    """The unit of measure for a pricing's lead time.

    Attributes
    ----------
    DAYS : str
        Lead time expressed in days.
    WEEKS : str
        Lead time expressed in weeks.
    MONTHS : str
        Lead time expressed in months.
    """

    DAYS = "Days"
    WEEKS = "Weeks"
    MONTHS = "Months"


class Pricing(BaseResource):
    """A price entry for an Inventory Item at a given company and location.

    A pricing records the cost of a material
    (:class:`~albert.resources.inventory.InventoryItem`) from a particular
    company, at a particular location. A single item can have many pricings.
    Create pricings with
    :meth:`~albert.collections.pricings.PricingCollection.create`.

    Attributes
    ----------
    id : str | None
        The Albert ID of the pricing. Set when the pricing is retrieved from Albert.
    inventory_id : str | None
        The Inventory ID of the item this pricing is for (format ``INV...``).
    company : Company
        The company the price is quoted from.
    location : Location
        The location the price applies to.
    description : str | None
        Free-text description of the pricing.
    pack_size : str | None
        The pack size the price is quoted for. Used to derive cost per unit.
    price : float
        The price, expressed per kilogram or per liter (currency/kg or
        currency/L) depending on the item's unit of measure. Convert to that
        basis before setting.
    currency : str
        The currency code for ``price``. Defaults to ``"USD"``.
    fob : str | None
        The FOB (free-on-board) shipping term for the pricing.
    lead_time : int | None
        The lead time value, in the unit given by ``lead_time_unit``.
    lead_time_unit : LeadTimeUnit | None
        The unit of measure for ``lead_time``.
    expiration_date : str | None
        The date the pricing expires, in ``YYYY-MM-DD`` format.
    default : int | None
        Whether this is the default pricing for the item. Read-only.

    Examples
    --------
    !!! example
        ```python
        from albert.resources.pricings import Pricing
        from albert.resources.companies import Company
        from albert.resources.locations import Location

        pricing = Pricing(
            inventory_id="INVA1",
            company=Company(name="Acme Chemicals"),
            location=Location(name="Pittsburgh"),
            price=12.50,
        )
        ```
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
    """The pricings belonging to a single Inventory Item.

    Returned by
    :meth:`~albert.collections.pricings.PricingCollection.get_by_inventory_ids`
    to group each item's pricings under its inventory ID.

    Attributes
    ----------
    inventory_id : str
        The Inventory ID the pricings belong to (format ``INV...``).
    pricings : list[Pricing]
        The pricings for that item.
    """

    inventory_id: InventoryId = Field(..., alias="id")
    pricings: list[Pricing]


class PricingBy(str, Enum):
    """A dimension to group or filter pricings by.

    Attributes
    ----------
    LOCATION : str
        Group or filter pricings by location.
    COMPANY : str
        Group or filter pricings by company.
    """

    LOCATION = "Location"
    COMPANY = "Company"
