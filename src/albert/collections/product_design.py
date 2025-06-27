from typing import Literal

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import InventoryId
from albert.resources.product_design import UnpackedProductDesign


class ProductDesignCollection(BaseCollection):
    """ProductDesignCollection is a collection class for managing Product Design entities in the Albert platform."""

    _updatable_attributes = {}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the CasCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{ProductDesignCollection._api_version}/productdesign"

    @validate_call
    def get_unpacked_products(
        self,
        *,
        inventory_ids: list[InventoryId],
        unpack_id: Literal["DESIGN", "PREDICTION"] = "PREDICTION",
    ) -> list[UnpackedProductDesign]:
        """
        Get unpacked products by inventory IDs.

        Parameters
        ----------
        inventory_ids : list[InventoryId]
            The inventory ids to get unpacked formulas for.
        unpack_id: Literal["DESIGN", "PREDICTION"]
            The ID for the unpack operation.

        Returns
        -------
        list[UnpackedProductDesign]
            The unpacked products/formulas.
        """
        url = f"{self.base_path}/{unpack_id}/unpack"
        batches = [inventory_ids[i : i + 50] for i in range(0, len(inventory_ids), 50)]
        return [
            UnpackedProductDesign(**item)
            for batch in batches
            for item in self.session.get(url, params={"formulaId": batch}).json()
        ]
