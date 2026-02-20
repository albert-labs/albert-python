from collections.abc import Iterator
from decimal import Decimal
from typing import Literal

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.users import UserCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import (
    InventoryId,
    LotId,
    StorageLocationId,
    TaskId,
    UserId,
)
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.core.utils import ensure_list
from albert.resources.inventory import InventoryCategory
from albert.resources.lots import Lot, LotAdjustmentAction, LotSearchItem

# 14 decimal places for inventory on hand delta calculations
DECIMAL_DELTA_QUANTIZE = Decimal("0.00000000000000")


class LotCollection(BaseCollection):
    """LotCollection is a collection class for managing Lot entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {
        "metadata",
        "storage_location",
        "manufacturer_lot_number",
        "expiration_date",
        "initial_quantity",
        "inventory_on_hand",
        "cost",
        "status",
        "pack_size",
        "barcode_id",
    }

    def __init__(self, *, session: AlbertSession):
        """A collection for interacting with Lots in Albert.

        Parameters
        ----------
        session : AlbertSession
            An Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{LotCollection._api_version}/lots"

    def create(self, *, lots: list[Lot]) -> list[Lot]:
        """Create new lots.

        Parameters
        ----------
        lots : list[Lot]
            A list of Lot entities to create.

        Returns
        -------
        list[Lot]
            A list of created Lot entities.
        """
        payload = [lot.model_dump(by_alias=True, exclude_none=True, mode="json") for lot in lots]
        response = self.session.post(self.base_path, json=payload)
        data = response.json()

        if isinstance(data, list):
            created_raw, failed = data, []
        else:
            created_raw = data.get("CreatedLots") or data.get("CreatedItems") or []
            failed = data.get("FailedItems") or []

        if (response.status_code == 206 or failed) and failed:
            logger.warning("Partial success creating lots", extra={"failed": failed})

        return [Lot(**lot) for lot in created_raw]

    @validate_call
    def get_by_id(self, *, id: LotId) -> Lot:
        """Get a lot by its ID.

        Parameters
        ----------
        id : str
            The ID of the lot to get.

        Returns
        -------
        Lot
            The lot with the provided ID.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Lot(**response.json())

    @validate_call
    def get_by_ids(self, *, ids: list[LotId]) -> list[Lot]:
        """Get a list of lots by their IDs.

        Parameters
        ----------
        ids : list[str]
            A list of lot IDs to get.

        Returns
        -------
        list[Lot]
            A list of lots with the provided IDs.
        """
        url = f"{self.base_path}/ids"
        response = self.session.get(url, params={"id": ids})
        return [Lot(**lot) for lot in response.json()["Items"]]

    @validate_call
    def delete(self, *, id: LotId) -> None:
        """Delete a lot by its ID.

        Parameters
        ----------
        id : str
            The ID of the lot to delete.
        """
        url = f"{self.base_path}?id={id}"
        self.session.delete(url)

    @validate_call
    def search(
        self,
        *,
        text: str | None = None,
        inventory_id: InventoryId | list[InventoryId] | None = None,
        location_id: str | list[str] | None = None,
        storage_location_id: str | list[str] | None = None,
        task_id: TaskId | list[TaskId] | None = None,
        category: InventoryCategory | str | list[InventoryCategory | str] | None = None,
        external_barcode_id: str | list[str] | None = None,
        search_field: str | list[str] | None = None,
        source_field: str | list[str] | None = None,
        additional_field: str | list[str] | None = None,
        is_drop_down: bool | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        sort_by: str | None = None,
        offset: int | None = None,
        max_items: int | None = None,
    ) -> Iterator[LotSearchItem]:
        """
        Search for Lot records matching the provided filters.

        ⚠️ This method returns partial (unhydrated) entities to optimize performance.
        To retrieve fully detailed entities, use :meth:`get_all` instead.

        Parameters
        ----------
        text : str, optional
            Free-text query matched against lot fields.
        inventory_id : InventoryId or list[InventoryId], optional
            Filter by parent inventory IDs.
        location_id : str or list[str], optional
            Filter by specific location IDs.
        storage_location_id : str or list[str], optional
            Filter by storage location IDs.
        task_id : TaskId or list[TaskId], optional
            Filter by source task IDs.
        category : InventoryCategory or list[str], optional
            Filter by parent inventory categories.
        external_barcode_id : str or list[str], optional
            Filter by external barcode IDs.
        search_field : str or list[str], optional
            Restrict the fields the `text` query searches.
        source_field : str or list[str], optional
            Restrict which fields are returned in the response.
        additional_field : str or list[str], optional
            Request additional columns from the search index.
        is_drop_down : bool, optional
            Use dropdown sanitization for the search text when True.
        order_by : OrderBy, optional
            Sort order for the results, default DESCENDING.
        sort_by : str, optional
            Attribute to sort by.
        offset : int, optional
            Pagination offset to start from.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[LotSearchItem]
            An iterator of matching partial (unhydrated) lot entities.
        """

        search_text = text if (text is None or len(text) < 50) else text[:50]

        params = {
            "offset": offset,
            "order": order_by,
            "text": search_text,
            "sortBy": sort_by,
            "isDropDown": is_drop_down,
            "inventoryId": ensure_list(inventory_id),
            "locationId": ensure_list(location_id),
            "storageLocationId": ensure_list(storage_location_id),
            "taskId": ensure_list(task_id),
            "category": ensure_list(category),
            "externalBarcodeId": ensure_list(external_barcode_id),
            "searchField": ensure_list(search_field),
            "sourceField": ensure_list(source_field),
            "additionalField": ensure_list(additional_field),
        }
        params = {key: value for key, value in params.items() if value is not None}

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [
                LotSearchItem(**item)._bind_collection(self) for item in items
            ],
        )

    @validate_call
    def get_all(
        self,
        *,
        parent_id: InventoryId | None = None,
        inventory_id: InventoryId | None = None,
        barcode_id: str | None = None,
        parent_id_category: str | None = None,
        inventory_on_hand: str | None = None,
        location_id: str | None = None,
        exact_match: bool = False,
        begins_with: bool = False,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Lot]:
        """
        Get all Lot entities with optional filters.

        Parameters
        ----------
        parent_id : str, optional
            Fetch lots for the given parentId (inventory).
        inventory_id : str, optional
            Fetch lots for the given inventoryId.
        barcode_id : str, optional
            Fetch lots for the given barcodeId.
        parent_id_category : str, optional
            Filter by parentIdCategory (e.g., RawMaterials, Consumables).
        inventory_on_hand : str, optional
            Filter by inventoryOnHand (lteZero, gtZero, eqZero).
        location_id : str, optional
            Filter by locationId.
        exact_match : bool, optional
            Whether to match barcodeId exactly. Default is False.
        begins_with : bool, optional
            Whether to match barcodeId as prefix. Default is False.
        start_key : str, optional
            The pagination key to continue listing from.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[Lot]
            An iterator of Lot entities matching the filters.
        """
        params = {
            "parentId": parent_id,
            "inventoryId": inventory_id,
            "barcodeId": barcode_id,
            "parentIdCategory": parent_id_category,
            "inventoryOnHand": inventory_on_hand,
            "locationId": location_id,
            "startKey": start_key,
            "exactMatch": exact_match,
            "beginsWith": begins_with,
        }

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [Lot(**item) for item in items],
        )

    def _generate_lots_patch_payload(self, *, existing: Lot, updated: Lot) -> PatchPayload:
        """Generate a patch payload for a lot, handling inventory_on_hand separately."""
        patch_data = super()._generate_patch_payload(
            existing=existing, updated=updated, generate_metadata_diff=True
        )
        # inventory on hand is a special case, where the API expects a delta
        if (
            updated.inventory_on_hand is not None
            and updated.inventory_on_hand != existing.inventory_on_hand
        ):
            patch_data.data = [d for d in patch_data.data if d.attribute != "inventoryOnHand"]
            delta = Decimal(str(updated.inventory_on_hand)) - Decimal(
                str(existing.inventory_on_hand)
            )
            delta = delta.quantize(DECIMAL_DELTA_QUANTIZE)  # 14 decimal places
            patch_data.data.append(
                PatchDatum(
                    attribute="inventoryOnHand",
                    operation=PatchOperation.UPDATE,
                    new_value=format(delta, "f"),
                    old_value=str(existing.inventory_on_hand),
                )
            )

        # Handle StorageLocation field name differences
        # API expects only the ID for the new and old values
        for datum in patch_data.data:
            if datum.attribute == "StorageLocation":
                datum.attribute = "storageLocation"
                datum.new_value = datum.new_value.id if datum.new_value else None
                datum.old_value = datum.old_value.id if datum.old_value else None

        return patch_data

    @staticmethod
    def _format_inventory_value(value: float) -> str:
        """Format inventory values without truncating decimal precision."""
        return format(Decimal(str(value)), "f")

    @staticmethod
    def _format_inventory_delta(value: Decimal) -> str:
        """Format inventory deltas to the API-required 14 decimal places."""
        return format(value.quantize(DECIMAL_DELTA_QUANTIZE), "f")

    @validate_call
    def adjust(
        self,
        *,
        lot_id: LotId,
        action: LotAdjustmentAction,
        quantity: float | None = None,
        description: str | None = None,
    ) -> Lot:
        """Adjust inventory lot.

        Parameters
        ----------
        lot_id : LotId
            The lot to adjust.
        action : LotAdjustmentAction
            Adjustment action to apply (ADD, SUBTRACT, SET, ZERO).
        quantity : float | None, optional
            Adjustment quantity. Required for ADD/SUBTRACT/SET and disallowed for ZERO.
        description : str | None, optional
            Optional description for the adjustment.

        Returns
        -------
        Lot
            The refreshed lot after adjustment.
        """
        if action == LotAdjustmentAction.ZERO and quantity is not None:
            raise ValueError("quantity must be omitted for ZERO action.")

        if action != LotAdjustmentAction.ZERO and (quantity is None or quantity <= 0):
            raise ValueError("quantity must be greater than zero for ADD, SUBTRACT, and SET.")

        existing_lot = self.get_by_id(id=lot_id)
        current = Decimal(str(existing_lot.inventory_on_hand))
        requested_quantity = Decimal(str(quantity)) if quantity is not None else None

        if action == LotAdjustmentAction.ADD:
            delta = requested_quantity
        elif action == LotAdjustmentAction.SUBTRACT:
            delta = -requested_quantity
        elif action == LotAdjustmentAction.SET:
            delta = requested_quantity - current
        else:
            delta = -current

        patch_payload = PatchPayload(
            data=[
                PatchDatum(
                    operation=PatchOperation.UPDATE,
                    attribute="inventoryOnHand",
                    old_value=str(existing_lot.inventory_on_hand),
                    new_value=self._format_inventory_delta(delta),
                )
            ]
        )
        payload = patch_payload.model_dump(mode="json", by_alias=True)
        if description is not None:
            payload["notes"] = description

        self.session.patch(f"{self.base_path}/{lot_id}", json=payload)
        return self.get_by_id(id=lot_id)

    @validate_call
    def transfer(
        self,
        *,
        lot_id: LotId,
        quantity: float | Literal["ALL"],
        storage_location_id: StorageLocationId,
        owner: UserId | None = None,
    ) -> Lot:
        """Transfer inventory lot to another location.

        Parameters
        ----------
        lot_id : LotId
            The source lot to transfer.
        quantity : float | Literal["ALL"]
            Quantity to transfer from the source lot, or "ALL" to transfer the full current
            inventory on hand.
        storage_location_id : StorageLocationId
            Destination storage location ID.
        owner : UserId | None, optional
            User ID of the Owner for the new lot. Defaults to the current user.

        Returns
        -------
        Lot
            The updated source lot for "ALL" transfers, otherwise the lot created by split.
        """
        if quantity == "ALL":
            source_lot = self.get_by_id(id=lot_id)
            patch_payload = PatchPayload(
                data=[
                    PatchDatum(
                        operation=PatchOperation.UPDATE,
                        attribute="storageLocation",
                        old_value=source_lot.storage_location.id
                        if source_lot.storage_location
                        else None,
                        new_value=storage_location_id,
                    )
                ]
            )
            self.session.patch(
                f"{self.base_path}/{lot_id}",
                json=patch_payload.model_dump(mode="json", by_alias=True),
            )
            return self.get_by_id(id=lot_id)

        transfer_quantity = quantity
        if transfer_quantity <= 0:
            raise ValueError("quantity must be greater than zero for transfer.")

        if owner is None:
            current_user = UserCollection(session=self.session).get_current_user()
            owner = current_user.id
            if owner is None:
                raise ValueError("Current user lookup failed to return a valid user id.")

        payload = {
            "action": "splitted",
            "inventoryOnHand": self._format_inventory_value(transfer_quantity),
            "StorageLocation": {"id": storage_location_id},
            "Owner": [{"id": owner}],
        }
        response = self.session.post(f"{self.base_path}/{lot_id}/split", json=payload)
        return Lot(**response.json())

    def update(self, *, lot: Lot) -> Lot:
        """Update a lot.

        Parameters
        ----------
        lot : Lot
            The updated lot object.

        Returns
        -------
        Lot
            The updated Lot entity as returned by the server.
        """
        existing_lot = self.get_by_id(id=lot.id)
        patch_data = self._generate_lots_patch_payload(existing=existing_lot, updated=lot)
        url = f"{self.base_path}/{lot.id}"
        if patch_data.data:
            self.session.patch(url, json=patch_data.model_dump(mode="json", by_alias=True))

        return self.get_by_id(id=lot.id)
