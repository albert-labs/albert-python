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
    """Manage Lots in the Albert platform.

    A Lot is a specific physical batch or quantity of an Inventory Item, for
    example a received shipment or a produced amount. Each lot tracks
    lot-specific details such as how much is currently on hand, where it is
    stored, its cost, and who owns it. Every lot belongs to exactly one
    Inventory Item (its parent), referenced by the parent Inventory ID
    (format ``INV...``); a lot's own ID has the format ``LOT...``.

    Lots are referenced throughout property data: a ``lot_id`` scopes results to
    a specific physical batch. Some lots are produced by a Task and carry a
    ``task_id`` linking them back to that Task.

    Inventory Items themselves are managed through the Inventory collection
    ([`InventoryCollection`][albert.collections.inventory.InventoryCollection]).

    This collection is accessed as ``client.lots``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for lot requests.

    Methods
    -------
    create(lots) -> list[Lot]
        Create one or more new lots.
    get_by_id(id) -> Lot
        Get a single lot by its ID.
    get_by_ids(ids) -> list[Lot]
        Get many lots by their IDs.
    search(...) -> Iterator[LotSearchItem]
        Fast, lightweight search returning partial lots (best for lookups/counts).
    get_all(...) -> Iterator[Lot]
        Return fully populated lots matching the given filters.
    adjust(lot_id, action, quantity=None, description=None) -> Lot
        Adjust a lot's inventory on hand (add, subtract, set, or zero).
    transfer(lot_id, quantity, storage_location_id, owner=None) -> Lot
        Move some or all of a lot's quantity to another storage location.
    update(lot) -> Lot
        Update an existing lot.
    delete(id) -> None
        Delete a lot by its ID.

    Examples
    --------
    ```python
    from albert import Albert
    client = Albert()
    # Look up all lots of a given inventory item
    lots = client.lots.get_all(parent_id="INVA1")
    for lot in lots:
        print(lot.id, lot.inventory_on_hand)
    ```
    """

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
        "owner",
    }

    def __init__(self, *, session: AlbertSession):
        """Initialize a LotCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{LotCollection._api_version}/lots"

    def create(self, *, lots: list[Lot]) -> list[Lot]:
        """Create one or more new lots.

        Use this to register physical batches against an existing Inventory Item
        (each lot's ``inventory_id`` must point at its parent item). Both regular
        lots and Task-produced lots can be created here.

        Parameters
        ----------
        lots : list[Lot]
            The lots to create. Each lot requires ``inventory_id`` (the parent
            Inventory ID). For a regular lot (no ``task_id``), ``storage_location``
            and ``initial_quantity`` are also required. For a Task lot (with a
            ``task_id``), ``location`` is required instead.

        Returns
        -------
        list[Lot]
            The created lots, each populated with its assigned Lot ID.

        Raises
        ------
        ValueError
            If a regular lot is missing ``storage_location`` or
            ``initial_quantity``, or a Task lot is missing ``location``.

        Notes
        -----
        If the API reports a partial success (some lots failed to create), a
        warning is logged and only the successfully created lots are returned.

        Examples
        --------
        ```python
        from albert import Albert
        from albert.resources.lots import Lot
        from albert.resources.storage_locations import StorageLocation
        client = Albert()
        new_lot = Lot(
            inventory_id="INVA1",
            storage_location=StorageLocation(name="Main Warehouse", id="STLA1"),
            initial_quantity=10.0,
        )
        created = client.lots.create(lots=[new_lot])
        created[0].id
        # 'LOTA1'
        ```
        """
        for lot in lots:
            if lot.task_id is None:
                if lot.storage_location is None:
                    raise ValueError("storage_location is required when creating a non-task lot.")
                if lot.initial_quantity is None:
                    raise ValueError("initial_quantity is required when creating a non-task lot.")
            else:
                if lot.location is None:
                    raise ValueError("location is required when creating a task lot.")

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
        """Get a single, fully populated lot by its ID.

        To retrieve many lots at once, use [`get_by_ids`][albert.collections.lots.LotCollection.get_by_ids]. To find lots
        without knowing their IDs, use [`search`][albert.collections.lots.LotCollection.search] or [`get_all`][albert.collections.lots.LotCollection.get_all].

        Parameters
        ----------
        id : LotId
            The Lot ID to retrieve (format ``LOT...``).

        Returns
        -------
        Lot
            The fully populated lot.

        Examples
        --------
        ```python
        from albert import Albert
        client = Albert()
        lot = client.lots.get_by_id(id="LOTA1")
        lot.inventory_on_hand
        # 10.0
        ```
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Lot(**response.json())

    @validate_call
    def get_by_ids(self, *, ids: list[LotId]) -> list[Lot]:
        """Get many fully populated lots by their IDs.

        Use this instead of repeated [`get_by_id`][albert.collections.lots.LotCollection.get_by_id] calls when you already
        have several Lot IDs to fetch.

        Parameters
        ----------
        ids : list[LotId]
            The Lot IDs to retrieve (format ``LOT...``).

        Returns
        -------
        list[Lot]
            The lots matching the provided IDs.

        Examples
        --------
        ```python
        from albert import Albert
        client = Albert()
        lots = client.lots.get_by_ids(ids=["LOTA1", "LOTA2"])
        ```
        """
        url = f"{self.base_path}/ids"
        response = self.session.get(url, params={"id": ids})
        return [Lot(**lot) for lot in response.json()["Items"]]

    @validate_call
    def delete(self, *, id: LotId) -> None:
        """Delete a lot by its ID.

        Parameters
        ----------
        id : LotId
            The Lot ID to delete (format ``LOT...``).

        Returns
        -------
        None

        Examples
        --------
        ```python
        from albert import Albert
        client = Albert()
        client.lots.delete(id="LOTA1")
        ```
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
        """Search for lots matching the given filters.

        This is the fast way to look up lots or count matches. It returns partial
        (unhydrated) lots ([`LotSearchItem`][albert.resources.lots.LotSearchItem]) rather
        than full ones, so it is well suited to lookups. When you need every field
        of each lot, use [`get_all`][albert.collections.lots.LotCollection.get_all] instead, or hydrate individual results.

        All filters are optional and combined together (AND). With no filters, all
        lots are returned.

        Parameters
        ----------
        text : str, optional
            Free-text query matched against lot fields. Truncated to 50 characters.
        inventory_id : InventoryId or list[InventoryId], optional
            Filter by parent Inventory ID(s) (format ``INV...``).
        location_id : str or list[str], optional
            Filter by location ID(s).
        storage_location_id : str or list[str], optional
            Filter by storage location ID(s) (format ``STL...``).
        task_id : TaskId or list[TaskId], optional
            Filter by the source Task ID(s) that produced the lots.
        category : InventoryCategory or list[str], optional
            Filter by the parent inventory category (e.g. ``RawMaterials``).
        external_barcode_id : str or list[str], optional
            Filter by external barcode ID(s).
        search_field : str or list[str], optional
            Restrict which fields the ``text`` query searches.
        source_field : str or list[str], optional
            Restrict which fields are returned in the response.
        additional_field : str or list[str], optional
            Request additional columns from the search index.
        is_drop_down : bool, optional
            Apply dropdown sanitization to the search text when True.
        order_by : OrderBy, optional
            Sort direction for the results. Defaults to ``OrderBy.DESCENDING``.
        sort_by : str, optional
            Attribute to sort by.
        max_items : int, optional
            Maximum number of lots to return in total. If None, returns all
            matching lots.

        Returns
        -------
        Iterator[LotSearchItem]
            An iterator over matching partial (unhydrated) lots.

        Examples
        --------
        ```python
        from albert import Albert
        client = Albert()
        # Find lots of a given inventory item that are running low
        for lot in client.lots.search(inventory_id="INVA1", max_items=50):
            print(lot.id, lot.parent_name)
        ```
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
        """Get fully populated lots matching the given filters.

        Same purpose as [`search`][albert.collections.lots.LotCollection.search], but returns fully populated
        [`Lot`][albert.resources.lots.Lot] objects (every field populated), which
        is slower. Use [`search`][albert.collections.lots.LotCollection.search] when a lightweight result is enough.

        All filters are optional and combined together (AND). A common use is
        passing ``parent_id`` to list every lot of one Inventory Item.

        Parameters
        ----------
        parent_id : InventoryId, optional
            Fetch lots whose parent is this Inventory ID (format ``INV...``).
        inventory_id : InventoryId, optional
            Fetch lots for the given inventory ID.
        barcode_id : str, optional
            Fetch lots with the given barcode ID.
        parent_id_category : str, optional
            Filter by the parent inventory category (e.g. ``RawMaterials``,
            ``Consumables``).
        inventory_on_hand : str, optional
            Filter by inventory on hand relative to zero. One of ``"lteZero"``,
            ``"gtZero"``, or ``"eqZero"``.
        location_id : str, optional
            Filter by location ID.
        exact_match : bool, optional
            Match ``barcode_id`` exactly. Defaults to False.
        begins_with : bool, optional
            Match ``barcode_id`` as a prefix. Defaults to False.
        start_key : str, optional
            Pagination key to continue listing from.
        max_items : int, optional
            Maximum number of lots to return in total. If None, returns all
            matching lots.

        Returns
        -------
        Iterator[Lot]
            An iterator over the fully populated lots matching the filters.

        Examples
        --------
        ```python
        from albert import Albert
        client = Albert()
        # List only lots of an item that still have stock
        for lot in client.lots.get_all(parent_id="INVA1", inventory_on_hand="gtZero"):
            print(lot.id, lot.inventory_on_hand)
        ```
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
        """Generate patch request data for a lot, handling inventory_on_hand separately."""
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

        # Owner is a list of users, but the API expects a single user ID string
        for datum in patch_data.data:
            if datum.attribute == "Owner":
                if datum.new_value and len(datum.new_value) > 1:
                    raise ValueError("A lot can only have one owner.")
                datum.new_value = datum.new_value[0].id if datum.new_value else None
                datum.old_value = datum.old_value[0].id if datum.old_value else None

        # Drop no-op owner updates where old and new values are identical after ID extraction
        patch_data.data = [
            d
            for d in patch_data.data
            if not (d.attribute == "Owner" and d.old_value == d.new_value)
        ]

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
        """Adjust a lot's inventory on hand.

        Use this to change how much of a lot is currently in stock, for example
        to record consumption, restocking, or a physical recount. To move
        quantity to a different storage location instead, use [`transfer`][albert.collections.lots.LotCollection.transfer].

        Parameters
        ----------
        lot_id : LotId
            The lot to adjust (format ``LOT...``).
        action : LotAdjustmentAction
            How to apply ``quantity`` to the current inventory on hand:

            - ``ADD``: increase on hand by ``quantity``.
            - ``SUBTRACT``: decrease on hand by ``quantity``.
            - ``SET``: set on hand to exactly ``quantity``.
            - ``ZERO``: set on hand to zero (no ``quantity``).
        quantity : float, optional
            The amount to apply. Required and must be greater than zero for
            ``ADD``, ``SUBTRACT``, and ``SET``; must be omitted for ``ZERO``.
        description : str, optional
            Free-text note recorded with the adjustment.

        Returns
        -------
        Lot
            The refreshed lot after the adjustment.

        Raises
        ------
        ValueError
            If ``quantity`` is supplied for ``ZERO``, or missing/non-positive for
            ``ADD``, ``SUBTRACT``, or ``SET``.

        Examples
        --------
        ```python
        from albert import Albert
        from albert.resources.lots import LotAdjustmentAction
        client = Albert()
        # Record that 2.5 units were consumed
        lot = client.lots.adjust(
            lot_id="LOTA1",
            action=LotAdjustmentAction.SUBTRACT,
            quantity=2.5,
            description="Used in experiment",
        )
        ```
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

        if delta != 0:
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
        """Transfer some or all of a lot's quantity to another storage location.

        Use this to physically relocate stock. Transferring ``"ALL"`` simply
        moves the source lot to the new storage location. Transferring a partial
        amount splits the source lot: the requested quantity is removed from the
        source and a new lot is created at the destination.

        To change how much is in stock (rather than where it is), use
        [`adjust`][albert.collections.lots.LotCollection.adjust].

        Parameters
        ----------
        lot_id : LotId
            The source lot to transfer from (format ``LOT...``).
        quantity : float or Literal["ALL"]
            The amount to transfer, or ``"ALL"`` to move the full current
            inventory on hand. A numeric quantity must be greater than zero.
        storage_location_id : StorageLocationId
            Destination storage location ID (format ``STL...``).
        owner : UserId, optional
            User ID (format ``USR...``) to own the destination lot. Defaults to
            the current user.

        Returns
        -------
        Lot
            The updated source lot for an ``"ALL"`` transfer; otherwise the new
            lot created by the split.

        Raises
        ------
        ValueError
            If a numeric ``quantity`` is not greater than zero, or the current
            user cannot be resolved when ``owner`` is omitted.

        Examples
        --------
        ```python
        from albert import Albert
        client = Albert()
        # Split 5 units off into a different storage location
        new_lot = client.lots.transfer(
            lot_id="LOTA1",
            quantity=5.0,
            storage_location_id="STLA2",
        )
        ```
        """
        if quantity == "ALL":
            source_lot = self.get_by_id(id=lot_id)
            current_location_id = (
                source_lot.storage_location.id if source_lot.storage_location else None
            )
            if current_location_id != storage_location_id:
                patch_payload = PatchPayload(
                    data=[
                        PatchDatum(
                            operation=PatchOperation.UPDATE,
                            attribute="storageLocation",
                            old_value=current_location_id,
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
        """Update an existing lot.

        Fetch the lot (e.g. with [`get_by_id`][albert.collections.lots.LotCollection.get_by_id]), modify the updatable fields
        on the returned object, then pass it here. Only the fields listed in Notes
        are applied. The lot is matched by its ``id``.

        For quantity changes, prefer [`adjust`][albert.collections.lots.LotCollection.adjust]; for relocations, prefer
        [`transfer`][albert.collections.lots.LotCollection.transfer]. Both handle the inventory-on-hand bookkeeping for you.

        Parameters
        ----------
        lot : Lot
            The lot carrying the desired changes. Its ``id`` identifies the lot to
            update.

        Returns
        -------
        Lot
            The refreshed lot after the update.

        Notes
        -----
        The following fields can be updated: ``barcode_id``, ``cost``,
        ``expiration_date``, ``initial_quantity``, ``inventory_on_hand``,
        ``manufacturer_lot_number``, ``metadata``, ``owner``, ``pack_size``,
        ``status``, ``storage_location``.

        Examples
        --------
        ```python
        from albert import Albert
        client = Albert()
        lot = client.lots.get_by_id(id="LOTA1")
        lot.cost = 42.0
        updated = client.lots.update(lot=lot)
        ```
        """
        existing_lot = self.get_by_id(id=lot.id)
        patch_data = self._generate_lots_patch_payload(existing=existing_lot, updated=lot)
        url = f"{self.base_path}/{lot.id}"
        if patch_data.data:
            self.session.patch(url, json=patch_data.model_dump(mode="json", by_alias=True))

        return self.get_by_id(id=lot.id)
