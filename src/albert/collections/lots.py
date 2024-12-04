import json
from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.resources.lots import Lot
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class LotCollection(BaseCollection):
    _api_version = "v3"
    _updatable_attributes = {"metadata"}

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{LotCollection._api_version}/lots"

    def create(self, *, lots: list[Lot]) -> list[Lot]:
        # TODO: Once thi endpoint is fixed, go back to passing the whole list at once
        payload = [lot.model_dump(by_alias=True, exclude_none=True, mode="json") for lot in lots]
        all_lots = []
        for lot in payload:
            response = self.session.post(self.base_path, json=[lot])
            all_lots.append(Lot(**response.json()[0]))
        # response = self.session.post(self.base_path, json=payload)
        # return [Lot(**lot) for lot in response.json().get("CreatedLots", [])]
        return all_lots

    def get_by_id(self, *, id: str) -> Lot:
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Lot(**response.json())

    def delete(self, *, id: str) -> None:
        url = f"{self.base_path}?id={id}"
        self.session.delete(url)

    def list(
        self,
        *,
        limit: int = 100,
        start_key: str | None = None,
        parent_id: str | None = None,
        inventory_id: str | None = None,
        barcode_id: str | None = None,
        parent_id_category: str | None = None,
        inventory_on_hand: str | None = None,
        location_id: str | None = None,
        exact_match: bool = False,
        begins_with: bool = False,
    ) -> Iterator[Lot]:
        """
        Lists Lot entities with optional filters.

        Parameters
        ----------
        limit : int, optional
            The maximum number of Lots to return, by default 100.
        start_key : Optional[str], optional
            The primary key of the first item to evaluate for pagination.
        parent_id : Optional[str], optional
            Fetches list of lots for a parentId (inventory).
        inventory_id : Optional[str], optional
            Fetches list of lots for an inventory.
        barcode_id : Optional[str], optional
            Fetches list of lots for a barcodeId.
        parent_id_category : Optional[str], optional
            Fetches list of lots for a parentIdCategory (e.g., RawMaterials, Consumables).
        inventory_on_hand : Optional[str], optional
            Fetches records based on inventoryOnHand (lteZero, gtZero, eqZero).
        location_id : Optional[str], optional
            Fetches list of lots for a locationId.
        exact_match : bool, optional
            Determines if barcodeId field should be an exact match, by default False.
        begins_with : bool, optional
            Determines if barcodeId begins with a certain value, by default False.

        Returns
        -------
        Iterator[Lot]
            An iterator of Lot objects.
        """
        params = {
            "limit": limit,
            "startKey": start_key,
            "parentId": parent_id,
            "inventoryId": inventory_id,
            "barcodeId": barcode_id,
            "parentIdCategory": parent_id_category,
            "inventoryOnHand": inventory_on_hand,
            "locationId": location_id,
            "exactMatch": json.dumps(exact_match),
            "beginsWith": json.dumps(begins_with),
        }
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            deserialize=lambda items: [Lot(**item) for item in items],
        )
