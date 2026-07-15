from enum import Enum
from typing import Any

from pydantic import Field, NonNegativeFloat, field_serializer, field_validator

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import InventoryId, LotId
from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem, SerializeAsEntityLink
from albert.resources._mixins import HydrationMixin
from albert.resources.inventory import InventoryCategory
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocation
from albert.resources.users import User


class LotStatus(str, Enum):
    """The lifecycle status of a lot.

    Attributes
    ----------
    ACTIVE
        The lot is in normal use.
    INACTIVE
        The lot is no longer in use.
    QUARANTINED
        The lot is held back from use (e.g. pending inspection).
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    QUARANTINED = "quarantined"


class LotAdjustmentAction(str, Enum):
    """How a quantity adjustment is applied to a lot's inventory on hand.

    Used with :meth:`~albert.collections.lots.LotCollection.adjust`.

    Attributes
    ----------
    ADD
        Increase inventory on hand by the given quantity.
    SUBTRACT
        Decrease inventory on hand by the given quantity.
    SET
        Set inventory on hand to exactly the given quantity.
    ZERO
        Set inventory on hand to zero.
    """

    ADD = "ADD"
    SUBTRACT = "SUBTRACT"
    SET = "SET"
    ZERO = "ZERO"


class Lot(BaseResource):
    """A specific physical batch or quantity of an Inventory Item.

    A Lot represents one received shipment or produced amount of a parent
    Inventory Item (identified by ``inventory_id``), tracking batch-specific
    details such as how much is currently on hand, where it is stored, its cost,
    and who owns it. Lots are managed through the Lot collection
    (:class:`~albert.collections.lots.LotCollection`, accessed as
    ``client.lots``); their parent items live in the Inventory collection
    (:class:`~albert.collections.inventory.InventoryCollection`). A ``lot_id``
    is used throughout property data to scope results to a single batch.

    A lot's own ID has the format ``LOT...``; its parent ``inventory_id`` has the
    format ``INV...``.

    Attributes
    ----------
    id : LotId | None
        The lot's Albert ID (format ``LOT...``). Assigned by Albert; present on
        lots retrieved from the platform.
    inventory_id : InventoryId
        The Albert ID of the parent Inventory Item this lot is a batch of.
    task_id : str | None
        The Albert ID of the Task that produced this lot, if it came from one.
    notes : str | None
        Free-text notes on the lot.
    expiration_date : str | None
        The date the lot expires, in ``YYYY-MM-DD`` format.
    manufacturer_lot_number : str | None
        The manufacturer's own lot number for this batch.
    storage_location : StorageLocation | None
        The specific place within a location where the lot is stored (e.g. a bin,
        cabinet, or hood).
    pack_size : str | None
        The pack size of the lot, used to calculate cost per unit.
    initial_quantity : NonNegativeFloat | None
        The quantity the lot started with, in the parent item's units.
    cost : NonNegativeFloat | None
        The cost of the lot.
    inventory_on_hand : NonNegativeFloat
        The quantity currently in stock, in the parent item's units. Change it
        with :meth:`~albert.collections.lots.LotCollection.adjust` rather than by
        editing directly.
    owner : list[User] | None
        The user(s) who own the lot. A lot may have at most one owner.
    lot_number : str | None
        The lot's number within Albert.
    external_barcode_id : str | None
        An external barcode ID for the lot.
    metadata : dict[str, str | list[EntityLink] | EntityLink] | None
        Custom field values for the lot. Allowed keys and values are defined by
        the Custom Fields configuration.
    action : str | None
        Internal marker for the operation that produced the lot (e.g. a split).
        Not typically set by callers.
    status : LotStatus | None
        The lot's lifecycle status. Read-only.
    location : Location | None
        The site/campus the lot is at (may contain multiple buildings, each with many
        storage locations).
    has_notes : bool | None
        Whether the lot has notes. Read-only.
    has_attachments : bool | None
        Whether the lot has attachments. Read-only.
    parent_name : str | None
        The name of the parent Inventory Item. Read-only.
    parent_unit : str | None
        The unit of measure of the parent Inventory Item. Read-only.
    parent_category : InventoryCategory | None
        The category of the parent Inventory Item (e.g. ``RawMaterials``).
        Read-only.
    barcode_id : str | None
        The barcode ID assigned by Albert. Read-only.
    task_completion_date : str | None
        The completion date of the Task that produced the lot. Read-only.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert
        from albert.resources.lots import Lot
        from albert.resources.storage_locations import StorageLocation
        client = Albert()
        lot = Lot(
            inventory_id="INVA1",
            storage_location=StorageLocation(name="Main Warehouse", id="STLA1"),
            initial_quantity=10.0,
        )
        created = client.lots.create(lots=[lot])
        ```
    """

    action: str | None = Field(default=None)
    id: LotId | None = Field(None, alias="albertId")
    inventory_id: InventoryId = Field(alias="parentId")
    task_id: str | None = Field(default=None, alias="taskId")
    expiration_date: str | None = Field(None, alias="expirationDate")
    manufacturer_lot_number: str | None = Field(None, alias="manufacturerLotNumber")
    storage_location: SerializeAsEntityLink[StorageLocation] | None = Field(
        alias="StorageLocation", default=None
    )
    pack_size: str | None = Field(None, alias="packSize")
    initial_quantity: float | None = Field(default=None, alias="initialQuantity")
    cost: NonNegativeFloat | None = Field(default=None)
    inventory_on_hand: float = Field(alias="inventoryOnHand")
    owner: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="Owner")
    lot_number: str | None = Field(None, alias="lotNumber")
    external_barcode_id: str | None = Field(None, alias="externalBarcodeId")
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)
    notes: str | None = Field(default=None)
    # because quarantined is an allowed Lot status, we need to extend the normal status

    # API-returned fields (read-only)
    status: LotStatus | None = Field(default=None, exclude=True, frozen=True)
    location: SerializeAsEntityLink[Location] | None = Field(
        default=None,
        alias="Location",
    )
    has_notes: bool | None = Field(default=None, alias="hasNotes", exclude=True, frozen=True)
    has_attachments: bool | None = Field(
        default=None,
        alias="hasAttachments",
        exclude=True,
        frozen=True,
    )
    parent_name: str | None = Field(default=None, alias="parentName", exclude=True, frozen=True)
    parent_unit: str | None = Field(default=None, alias="parentUnit", exclude=True, frozen=True)
    parent_category: InventoryCategory | None = Field(
        default=None,
        alias="parentCategory",
        exclude=True,
        frozen=True,
    )
    barcode_id: str | None = Field(default=None, alias="barcodeId", exclude=True, frozen=True)
    task_completion_date: str | None = Field(
        default=None, alias="taskCompletionDate", exclude=True, frozen=True
    )

    @field_validator("has_notes", mode="before")
    def validate_has_notes(cls, value: Any) -> Any:
        if value == "1":
            return True
        elif value == "0":
            return False
        return value

    @field_validator("has_attachments", mode="before")
    def validate_has_attachments(cls, value: Any) -> Any:
        if value == "1":
            return True
        elif value == "0":
            return False
        return value

    @staticmethod
    def _format_decimal(value: NonNegativeFloat) -> str:
        formatted = format(value, "f")
        if "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")
        return formatted

    @field_serializer("initial_quantity", return_type=str | None)
    def serialize_initial_quantity(self, initial_quantity: NonNegativeFloat):
        return self._format_decimal(initial_quantity) if initial_quantity is not None else None

    @field_serializer("cost", return_type=str | None)
    def serialize_cost(self, cost: NonNegativeFloat):
        return self._format_decimal(cost) if cost is not None else None

    @field_serializer("inventory_on_hand", return_type=str)
    def serialize_inventory_on_hand(self, inventory_on_hand: NonNegativeFloat):
        return self._format_decimal(inventory_on_hand)


class LotSearchItem(BaseAlbertModel, HydrationMixin[Lot]):
    """Lightweight, partial view of a :class:`Lot` returned by search.

    Returned by :meth:`~albert.collections.lots.LotCollection.search`. It carries
    only the most commonly needed fields for fast lookups; call
    :meth:`hydrate` to fetch the full :class:`Lot` when you need every field.

    Attributes
    ----------
    id : LotId
        The lot's Albert ID (format ``LOT...``).
    inventory_id : InventoryId | None
        The Albert ID of the parent Inventory Item.
    parent_name : str | None
        The name of the parent Inventory Item.
    parent_unit : str | None
        The unit of measure of the parent Inventory Item.
    parent_category : InventoryCategory | None
        The category of the parent Inventory Item (e.g. ``RawMaterials``).
    task_id : str | None
        The Albert ID of the Task that produced this lot, if any.
    barcode_id : str | None
        The barcode ID assigned by Albert.
    expiration_date : str | None
        The date the lot expires, in ``YYYY-MM-DD`` format.
    manufacturer_lot_number : str | None
        The manufacturer's own lot number for this batch.
    lot_number : str | None
        The lot's number within Albert.
    """

    id: LotId = Field(alias="albertId")
    inventory_id: InventoryId | None = Field(default=None, alias="parentId")
    parent_name: str | None = Field(default=None, alias="parentName")
    parent_unit: str | None = Field(default=None, alias="parentUnit")
    parent_category: InventoryCategory | None = Field(default=None, alias="parentIdCategory")
    task_id: str | None = Field(default=None, alias="taskId")
    barcode_id: str | None = Field(default=None, alias="barcodeId")
    expiration_date: str | None = Field(default=None, alias="expirationDate")
    manufacturer_lot_number: str | None = Field(default=None, alias="manufacturerLotNumber")
    lot_number: str | None = Field(default=None, alias="number")
