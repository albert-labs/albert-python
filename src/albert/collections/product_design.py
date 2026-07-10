from typing import Literal

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import InventoryId
from albert.resources.product_design import UnpackedProductDesign


class ProductDesignCollection(BaseCollection):
    """Unpack formulated products into their full substance-level composition.

    "Product design" here refers to unpacking (flattening) a formulation inventory
    item into the complete set of substances it is made of. A formula in Albert is
    built from other inventory items, which may themselves be formulas; unpacking
    walks that hierarchy all the way down and rolls it up into a single, CAS-level
    view of what the product actually contains. The result reports each constituent
    ingredient, its normalized amount, the CAS numbers involved, and the associated
    SDS / regulatory details (hazard class, UN number).

    Use this when you need the resolved composition of a formula rather than just
    its immediate ingredient list, for example to compute regulatory or safety
    rollups. The formulas being unpacked are Inventory Items in the ``Formulas``
    category (see :class:`~albert.collections.inventory.InventoryCollection`), and
    the substances resolve to CAS entries (see
    :class:`~albert.collections.cas.CasCollection`).

    This collection is accessed as ``client.product_design``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for product design requests.

    Methods
    -------
    get_unpacked_products(inventory_ids, unpack_id="PREDICTION") -> list[UnpackedProductDesign]
        Unpack one or more formulas into their full CAS-level substance composition.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert
        client = Albert()
        unpacked = client.product_design.get_unpacked_products(
            inventory_ids=["INVA1", "INVA2"],
        )
        for product in unpacked:
            for ingredient in product.inventories or []:
                print(ingredient.name, ingredient.value)
        ```
    """

    _updatable_attributes = {}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a ProductDesignCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
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
        """Unpack formulas into their full CAS-level substance composition.

        Each supplied formula is flattened into its constituent substances, with
        their amounts, CAS information, and SDS / regulatory details. One
        :class:`~albert.resources.product_design.UnpackedProductDesign` is returned
        per input formula. Requests are automatically split into batches of 50
        inventory IDs, so large lists can be passed in a single call.

        Parameters
        ----------
        inventory_ids : list[InventoryId]
            The formula Inventory IDs to unpack (format ``INV...``, e.g. ``"INVA1"``).
        unpack_id : {"DESIGN", "PREDICTION"}, optional
            Which unpacking mode the server should use. Defaults to ``"PREDICTION"``.

        Returns
        -------
        list[UnpackedProductDesign]
            The unpacked composition, one entry per input formula.

        Examples
        --------
        !!! example
            ```python
            unpacked = client.product_design.get_unpacked_products(
                inventory_ids=["INVA1"],
                unpack_id="DESIGN",
            )
            substances = unpacked[0].cas_level_substances or []
            for substance in substances:
                print(substance.cas_id, substance.amount)
            ```
        """
        url = f"{self.base_path}/{unpack_id}/unpack"
        batches = [inventory_ids[i : i + 50] for i in range(0, len(inventory_ids), 50)]
        return [
            UnpackedProductDesign(**item)
            for batch in batches
            for item in self.session.get(url, params={"formulaId": batch}).json()
        ]
