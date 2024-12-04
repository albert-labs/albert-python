from enum import Enum

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.pricings import Pricing
from albert.session import AlbertSession
from albert.utils.patches import PatchDatum, PatchOperation, PatchPayload


class PricingBy(str, Enum):
    LOCATION = "Location"
    COMPANY = "Company"


class PricingCollection(BaseCollection):
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
        super().__init__(session=session)
        self.base_path = f"/api/{PricingCollection._api_version}/pricings"

    def create(self, *, pricing: Pricing) -> Pricing:
        payload = pricing.model_dump(by_alias=True, exclude_none=True, mode="json")
        response = self.session.post(self.base_path, json=payload)
        return Pricing(**response.json())

    def get_by_id(self, *, id: str) -> Pricing:
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Pricing(**response.json())

    def get_by_inventory_id(
        self,
        *,
        inventory_id: str,
        group_by: PricingBy = None,
        filter_by: PricingBy = None,
        filter_id: str = None,
        order_by: OrderBy = None,
    ) -> Pricing:
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

    def delete(self, *, id: str) -> None:
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
        current_pricing = self.get_by_id(id=pricing.id)
        patch_payload = self._pricing_patch_payload(existing=current_pricing, updated=pricing)
        self.session.patch(
            url=f"{self.base_path}/{pricing.id}",
            json=patch_payload.model_dump(mode="json", by_alias=True),
        )
        return self.get_by_id(id=pricing.id)
