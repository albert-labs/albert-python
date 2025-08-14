from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy
from albert.core.shared.identifiers import InventoryId
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.resources.pricings import InventoryPricings, Pricing, PricingBy


class PricingCollection(BaseCollection):
    """PricingCollection is a collection class for managing Pricing entities in the Albert platform."""

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
        """Initializes the PricingCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{PricingCollection._api_version}/pricings"

    def create(self, *, pricing: Pricing) -> Pricing:
        """Creates a new Pricing entity.

        Parameters
        ----------
        pricing : Pricing
            The Pricing entity to create.

        Returns
        -------
        Pricing
            The created Pricing entity.
        """
        payload = pricing.model_dump(by_alias=True, exclude_none=True, mode="json")
        response = self.session.post(self.base_path, json=payload)
        return Pricing(**response.json())

    @validate_call
    def get_by_id(self, *, id: str) -> Pricing:
        """Retrieves a Pricing entity by its ID.

        Parameters
        ----------
        id : str
            The ID of the Pricing entity to retrieve.

        Returns
        -------
        Pricing
            The Pricing entity if found, None otherwise.
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
        """Returns a list of Pricing entities for the given inventory ID as per the provided parameters.

        Parameters
        ----------
        inventory_id : str
            The ID of the inventory to retrieve pricings for.
        group_by : PricingBy | None, optional
            Grouping by PricingBy, by default None
        filter_by : PricingBy | None, optional
            Filter by PricingBy, by default None
        filter_id : str | None, optional
            The string to use as the filter, by default None
        order_by : OrderBy | None, optional
            The order to sort the results by, by default None

        Returns
        -------
        list[Pricing]
            A list of Pricing entities matching the provided parameters.
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
        """Returns a list of Pricing resources for each parent inventory ID.

        Parameters
        ----------
        inventory_ids : list[str]
            The list of inventory IDs to retrieve pricings for.

        Returns
        -------
        list[InventoryPricing]
            A list of InventoryPricing entities matching the provided inventory.
        """
        params = {"id": inventory_ids}
        response = self.session.get(f"{self.base_path}/ids", params=params)
        return [InventoryPricings(**x) for x in response.json()["Items"]]

    @validate_call
    def delete(self, *, id: str) -> None:
        """Deletes a Pricing entity by its ID.

        Parameters
        ----------
        id : str
            The ID of the Pricing entity to delete.
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
        """Updates a Pricing entity.

        Parameters
        ----------
        pricing : Pricing
            The updated Pricing entity.

        Returns
        -------
        Pricing
            The updated Pricing entity as it appears in Albert.
        """
        current_pricing = self.get_by_id(id=pricing.id)
        patch_payload = self._pricing_patch_payload(existing=current_pricing, updated=pricing)
        self.session.patch(
            url=f"{self.base_path}/{pricing.id}",
            json=patch_payload.model_dump(mode="json", by_alias=True),
        )
        return self.get_by_id(id=pricing.id)
