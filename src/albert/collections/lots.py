from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.resources.lots import Lot


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

    def get_by_ids(self, *, ids: list[str]) -> list[Lot]:
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

    def delete(self, *, id: str) -> None:
        """Delete a lot by its ID.

        Parameters
        ----------
        id : str
            The ID of the lot to delete.
        """
        url = f"{self.base_path}?id={id}"
        self.session.delete(url)

    def get_all(
        self,
        *,
        parent_id: str | None = None,
        inventory_id: str | None = None,
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
        patch_data = self._generate_patch_payload(existing=existing_lot, updated=lot)
        url = f"{self.base_path}/{lot.id}"

        self.session.patch(url, json=patch_data.model_dump(mode="json", by_alias=True))

        return self.get_by_id(id=lot.id)
