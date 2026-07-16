from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy
from albert.core.shared.identifiers import InventoryId
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.resources.pricings import InventoryPricings, Pricing, PricingBy


class PricingCollection(BaseCollection):
    """Manage Pricing entries for Inventory Items in the Albert platform.

    A Pricing is a price entry for an Inventory Item
    ([`InventoryItem`][albert.resources.inventory.InventoryItem]): a cost for a given
    amount of the material, recorded for a specific company and location. An item
    can have many pricings (for example, different suppliers, sites, or pack
    sizes), so pricings are usually retrieved by the inventory item they belong to
    rather than one at a time.

    This collection is accessed as ``client.pricings``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for pricing requests.

    Methods
    -------
    create(pricing) -> Pricing
        Create a new pricing entry for an inventory item.
    get_by_id(id) -> Pricing
        Get a single pricing by its ID.
    get_by_inventory_id(inventory_id, ...) -> list[Pricing]
        Get the pricings for one inventory item, optionally grouped/filtered.
    get_by_inventory_ids(inventory_ids) -> list[InventoryPricings]
        Get pricings for several inventory items at once.
    update(pricing) -> Pricing
        Update an existing pricing.
    delete(id) -> None
        Delete a pricing by its ID.

    Examples
    --------
    ```python
    from albert import Albert

    client = Albert()
    pricings = client.pricings.get_by_inventory_id(inventory_id="INVA1")
    for pricing in pricings:
        print(pricing.price, pricing.currency)
    ```
    """

    _api_version = "v3"
    _updatable_attributes = {
        "pack_size",
        "price",
        "currency",
        "description",
        "fob",
        "expiration_date",
        "lead_time",
        "lead_time_unit",
        "inventory_id",
    }

    def __init__(self, *, session: AlbertSession):
        """Initialize a PricingCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{PricingCollection._api_version}/pricings"

    def create(self, *, pricing: Pricing) -> Pricing:
        """Create a new pricing entry for an inventory item.

        Parameters
        ----------
        pricing : Pricing
            The pricing to create. ``inventory_id``, ``company``, ``location``, and
            ``price`` identify the item, source, site, and cost; see
            [`Pricing`][albert.resources.pricings.Pricing].

        Returns
        -------
        Pricing
            The newly created pricing, populated with its assigned ID.

        Examples
        --------
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
        created = client.pricings.create(pricing=pricing)
        created.id
        ```
        """
        payload = pricing.model_dump(by_alias=True, exclude_none=True, mode="json")
        response = self.session.post(self.base_path, json=payload)
        return Pricing(**response.json())

    @validate_call
    def get_by_id(self, *, id: str) -> Pricing:
        """Get a single pricing by its ID.

        Parameters
        ----------
        id : str
            The ID of the pricing to retrieve.

        Returns
        -------
        Pricing
            The fully populated pricing.

        Examples
        --------
        ```python
        pricing = client.pricings.get_by_id(id="...")
        pricing.price
        ```
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Pricing(**response.json())

    @validate_call
    def get_by_inventory_id(
        self,
        *,
        inventory_id: InventoryId,
        group_by: PricingBy | None = None,
        filter_by: PricingBy | None = None,
        filter_id: str | None = None,
        order_by: OrderBy | None = None,
    ) -> list[Pricing]:
        """Get the pricings for a single inventory item.

        Returns every pricing entry attached to the given inventory item, with
        optional grouping, filtering, and sorting. To pull pricings for many items
        at once, use [`get_by_inventory_ids`][albert.collections.pricings.PricingCollection.get_by_inventory_ids].

        Parameters
        ----------
        inventory_id : str
            The Inventory ID to retrieve pricings for (format ``INV...``).
        group_by : PricingBy, optional
            Group the results by company or location. See
            [`PricingBy`][albert.resources.pricings.PricingBy].
        filter_by : PricingBy, optional
            The dimension (company or location) to filter on. Pair with
            ``filter_id``.
        filter_id : str, optional
            The ID to match on the ``filter_by`` dimension.
        order_by : OrderBy, optional
            Sort direction for the results.

        Returns
        -------
        list[Pricing]
            The pricings for the item matching the provided parameters.

        Examples
        --------
        ```python
        pricings = client.pricings.get_by_inventory_id(inventory_id="INVA1")
        [p.price for p in pricings]
        ```
        """
        params = {
            "parentId": inventory_id,
            "groupBy": group_by,
            "filterBy": filter_by,
            "id": filter_id,
            "orderBy": order_by,
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = self.session.get(self.base_path, params=params)
        items = response.json().get("Items", [])
        return [Pricing(**x) for x in items]

    @validate_call
    def get_by_inventory_ids(self, *, inventory_ids: list[InventoryId]) -> list[InventoryPricings]:
        """Get pricings for several inventory items at once.

        Each returned [`InventoryPricings`][albert.resources.pricings.InventoryPricings] groups
        one item's pricings under its inventory ID.

        Parameters
        ----------
        inventory_ids : list[str]
            The Inventory IDs to retrieve pricings for (format ``INV...``).

        Returns
        -------
        list[InventoryPricings]
            One entry per item, each holding that item's pricings.

        Examples
        --------
        ```python
        grouped = client.pricings.get_by_inventory_ids(
            inventory_ids=["INVA1", "INVA2"]
        )
        grouped[0].pricings
        ```
        """
        params = {"id": inventory_ids}
        response = self.session.get(f"{self.base_path}/ids", params=params)
        return [InventoryPricings(**x) for x in response.json()["Items"]]

    @validate_call
    def delete(self, *, id: str) -> None:
        """Delete a pricing by its ID.

        Parameters
        ----------
        id : str
            The ID of the pricing to delete.

        Returns
        -------
        None

        Examples
        --------
        ```python
        client.pricings.delete(id="...")
        ```
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def _pricing_patch_payload(self, *, existing: Pricing, updated: Pricing) -> PatchPayload:
        patch_payload = self._generate_patch_payload(existing=existing, updated=updated)
        for attr in ("company", "location"):
            # These must be set, so we don't need to worry about add or delete
            existing_attr = getattr(existing, attr).id
            updated_attr = getattr(updated, attr).id
            if existing_attr != updated_attr:
                patch_payload.data.append(
                    PatchDatum(
                        operation=PatchOperation.UPDATE,
                        attribute=f"{attr}Id",
                        old_value=existing_attr,
                        new_value=updated_attr,
                    )
                )
        return patch_payload

    def update(self, *, pricing: Pricing) -> Pricing:
        """Update an existing pricing.

        Fetch the pricing (e.g. with [`get_by_id`][albert.collections.pricings.PricingCollection.get_by_id]), modify the updatable
        fields on the returned object, then pass it here. The ``company`` and
        ``location`` links can also be reassigned.

        Parameters
        ----------
        pricing : Pricing
            The pricing to update. Must have a valid ``id``.

        Returns
        -------
        Pricing
            The updated pricing as it appears in Albert.

        Notes
        -----
        The following fields can be updated: ``currency``, ``description``,
        ``expiration_date``, ``fob``, ``inventory_id``, ``lead_time``,
        ``lead_time_unit``, ``pack_size``, ``price``.

        Examples
        --------
        ```python
        pricing = client.pricings.get_by_id(id="...")
        pricing.price = 15.00
        updated = client.pricings.update(pricing=pricing)
        updated.price
        # 15.0
        ```
        """
        current_pricing = self.get_by_id(id=pricing.id)
        patch_payload = self._pricing_patch_payload(existing=current_pricing, updated=pricing)
        self.session.patch(
            url=f"{self.base_path}/{pricing.id}",
            json=patch_payload.model_dump(mode="json", by_alias=True),
        )
        return self.get_by_id(id=pricing.id)
