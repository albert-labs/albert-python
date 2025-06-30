from enum import Enum
from typing import Any

from pydantic import Field, NonNegativeFloat, field_serializer, field_validator

from albert.core.shared.identifiers import InventoryId, LotId
from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem, SerializeAsEntityLink
from albert.resources.inventory import InventoryCategory
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocation
from albert.resources.users import User


class LotStatus(str, Enum):
    """The status of a lot"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    QUARANTINED = "quarantined"


class Lot(BaseResource):
    """A lot in Albert.

    Attributes
    ----------
    id : LotId | None
        The Albert ID of the lot. Set when the lot is retrieved from Albert.
    inventory_id : InventoryId
        The Albert ID of the inventory item associated with the lot.
    task_id : str | None
        The Albert ID of the task associated with the creation of lot. Optional.
    notes : str | None
        The notes associated with the lot. Optional.
    expiration_date : str | None
        The expiration date of the lot. YYYY-MM-DD format. Optional.
    manufacturer_lot_number : str | None
        The manufacturer lot number of the lot. Optional.
    storage_location : StorageLocation | None
        The storage location of the lot. Optional.
    pack_size : str | None
        The pack size of the lot. Optional. Used to calculate the cost per unit.
    initial_quantity : NonNegativeFloat | None
        The initial quantity of the lot. Optional.
    cost : NonNegativeFloat | None
        The cost of the lot. Optional.
    inventory_on_hand : NonNegativeFloat
        The inventory on hand of the lot.
    owner : list[User] | None
        The owners of the lot. Optional.
    lot_number : str | None
        The lot number of the lot. Optional.
    external_barcode_id : str | None
        The external barcode ID of the lot. Optional.
    metadata : dict[str, str | list[EntityLink] | EntityLink] | None
        The metadata of the lot. Optional. Metadata allowed values can be found using the Custom Fields API.
    has_notes : bool
        Whether the lot has notes. Read-only.
    has_attachments : bool
        Whether the lot has attachments. Read-only.
    barcode_id : str
        The barcode ID of the lot. Read-only.
    """

    id: LotId | None = Field(None, alias="albertId")
    inventory_id: InventoryId = Field(alias="parentId")
    task_id: str | None = Field(default=None, alias="taskId")
    expiration_date: str | None = Field(None, alias="expirationDate")
    manufacturer_lot_number: str | None = Field(None, alias="manufacturerLotNumber")
    storage_location: SerializeAsEntityLink[StorageLocation] | None = Field(
        alias="StorageLocation", default=None
    )
    pack_size: str | None = Field(None, alias="packSize")
    initial_quantity: NonNegativeFloat | None = Field(default=None, alias="initialQuantity")
    cost: NonNegativeFloat | None = Field(default=None)
    inventory_on_hand: float = Field(alias="inventoryOnHand")
    owner: list[SerializeAsEntityLink[User]] | None = Field(default=None, alias="Owner")
    lot_number: str | None = Field(None, alias="lotNumber")
    external_barcode_id: str | None = Field(None, alias="externalBarcodeId")
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)
    # because quarantined is an allowed Lot status, we need to extend the normal status
    status: LotStatus | None = Field(default=None)

    # Read-only fields
    location: SerializeAsEntityLink[Location] | None = Field(
        default=None,
        alias="Location",
        exclude=True,
        frozen=True,
    )
    notes: str | None = Field(default=None, exclude=True, frozen=True)
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
    barcode_id: str | None = Field(default=None, alias="barcodeId")

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

    @field_serializer("initial_quantity", return_type=str)
    def serialize_initial_quantity(self, initial_quantity: NonNegativeFloat):
        return str(initial_quantity)

    @field_serializer("cost", return_type=str)
    def serialize_cost(self, cost: NonNegativeFloat):
        return str(cost)

    @field_serializer("inventory_on_hand", return_type=str)
    def serialize_inventory_on_hand(self, inventory_on_hand: NonNegativeFloat):
        return str(inventory_on_hand)
