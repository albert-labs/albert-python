from collections.abc import Iterator
from typing import Any, Literal

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import InventoryId, ProjectId
from albert.core.utils import ensure_list
from albert.resources.product_design import ProductDesignSearchItem, UnpackedProductDesign

_SEARCH_PAGE_SIZE = 100  # maximum page size accepted by the product design search endpoint


class ProductDesignCollection(BaseCollection):
    """Search the product design grid and unpack formulated products.

    Two separate capabilities live here:

    - [`search`][albert.collections.product_design.ProductDesignCollection.search]
      discovers formulations on the product design grid by free text, facets, and
      project / inventory filters, returning lightweight formula hits.
    - [`get_unpacked_products`][albert.collections.product_design.ProductDesignCollection.get_unpacked_products]
      flattens a formulation inventory item into its full substance-level
      composition, described below.

    An unpacked product resolves a formulation's complete substance composition by
    recursively traversing its ingredient tree: each sub-formulation is expanded
    into its own ingredients, with fractional contributions multiplied down through
    each level and summed at the CAS-number level. It produces two outputs: a
    row-level inventory list (the direct worksheet ingredients, some of which may
    themselves be sub-formulations) and a flat CAS-level substance list (fully
    resolved raw materials with combined weight fractions).

    The calculation assumes a non-reactive, homogeneous mixture: no chemical
    transformations occur and concentrations are additive. When a formulation has
    overrides, the recursive traversal short-circuits; Albert accepts the declared
    composition at face value rather than deriving it, and CAS amounts are expressed
    as ranges to signal supplied (not bottom-up calculated) values.

    Use this when you need the resolved composition of a formula rather than just
    its immediate ingredient list, for example to compute regulatory or safety
    rollups. The formulas being unpacked are Inventory Items in the ``Formulas``
    category (see [`InventoryCollection`][albert.collections.inventory.InventoryCollection]), and
    the substances resolve to CAS entries (see
    [`CasCollection`][albert.collections.cas.CasCollection]).

    This collection is accessed as ``client.product_design``.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        unpacked = client.product_design.get_unpacked_products(
            inventory_ids=["INVA9999999", "INVA9999998"],
        )
        for product in unpacked:
            for ingredient in product.inventories or []:
                print(ingredient.name, ingredient.value)
        ```

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
    search(...) -> Iterator[ProductDesignSearchItem]
        Search for formulations on the product design grid matching the given filters.
    get_unpacked_products(inventory_ids, unpack_id="PREDICTION") -> list[UnpackedProductDesign]
        Unpack one or more formulas into their full CAS-level substance composition.
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
    def search(
        self,
        *,
        text: str | None = None,
        project_id: ProjectId | None = None,
        tags: str | list[str] | None = None,
        albert_id: str | list[str] | None = None,
        state: str | list[str] | None = None,
        data_template: str | list[str] | None = None,
        inventory_name: str | list[str] | None = None,
        inventory_id: str | list[str] | None = None,
        formula_created_by: str | list[str] | None = None,
        facet_text: str | None = None,
        facet_field: str | None = None,
        contains_field: str | list[str] | None = None,
        contains_text: str | list[str] | None = None,
        source_field: str | list[str] | None = None,
        product_grid: bool | None = None,
        sort_by: str | None = None,
        order: OrderBy | None = None,
        max_items: int | None = None,
    ) -> Iterator[ProductDesignSearchItem]:
        """Search for formulations on the product design grid matching the given filters.

        Returns lightweight, partially populated
        [`ProductDesignSearchItem`][albert.resources.product_design.ProductDesignSearchItem]
        hits, best for free-text lookups, counts, and pulling formula IDs. When you
        need the complete formula, pass the hit's ``id`` to
        [`get_by_id`][albert.collections.inventory.InventoryCollection.get_by_id].
        Results are returned as a lazily paginated iterator.

        !!! example
            ```python
            for hit in client.product_design.search(text="shampoo", max_items=10):
                print(hit.id, hit.name)
            ```

        Parameters
        ----------
        text : str, optional
            Free-text query matched against formula fields.
        project_id : ProjectId, optional
            Scope the search to a project (format ``PRO...``).
        tags : str or list[str], optional
            Filter by tag name(s).
        albert_id : str or list[str], optional
            Filter by formula Inventory ID(s) (format ``INV...``).
        state : str or list[str], optional
            Filter by formula lock/unlock state(s).
        data_template : str or list[str], optional
            Filter by data template name(s).
        inventory_name : str or list[str], optional
            Filter by ingredient name(s).
        inventory_id : str or list[str], optional
            Filter by ingredient Inventory ID(s).
        formula_created_by : str or list[str], optional
            Filter by formula creator(s).
        facet_text : str, optional
            Text to match within a facet search.
        facet_field : str, optional
            Field to search within for facet filtering.
        contains_field : str or list[str], optional
            Field(s) to apply a "contains" search to.
        contains_text : str or list[str], optional
            Text value(s) for the "contains" search.
        source_field : str or list[str], optional
            Restrict which fields are returned on each search hit.
        product_grid : bool, optional
            Search the product grid shown on the project homepage.
        sort_by : str, optional
            Attribute to sort results by.
        order : OrderBy, optional
            The order in which to sort results (``asc`` or ``desc``).
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matching items.

        Returns
        -------
        Iterator[ProductDesignSearchItem]
            A lazy iterator of matching formula hits.
        """
        params: dict[str, Any] = {
            "text": text,
            "projectId": project_id,
            "tags": ensure_list(tags),
            "albertId": ensure_list(albert_id),
            "state": ensure_list(state),
            "dataTemplate": ensure_list(data_template),
            "inventoryName": ensure_list(inventory_name),
            "inventoryId": ensure_list(inventory_id),
            "formulaCreatedBy": ensure_list(formula_created_by),
            "facetText": facet_text,
            "facetField": facet_field,
            "containsField": ensure_list(contains_field),
            "containsText": ensure_list(contains_text),
            "sourceField": ensure_list(source_field),
            "productGrid": product_grid,
            "sortBy": sort_by,
            "order": order,
            "limit": _SEARCH_PAGE_SIZE,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [ProductDesignSearchItem.model_validate(x) for x in items],
        )

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
        [`UnpackedProductDesign`][albert.resources.product_design.UnpackedProductDesign] is returned
        per input formula. Requests are automatically split into batches of 50
        inventory IDs, so large lists can be passed in a single call. To discover
        formula IDs by text or filters, use
        [`search`][albert.collections.product_design.ProductDesignCollection.search].

        !!! example
            ```python
            unpacked = client.product_design.get_unpacked_products(
                inventory_ids=["INVA9999999"],
                unpack_id="DESIGN",
            )
            substances = unpacked[0].cas_level_substances or []
            for substance in substances:
                print(substance.cas_id, substance.amount)
            ```

        Parameters
        ----------
        inventory_ids : list[InventoryId]
            The formula Inventory IDs to unpack (format ``INV...``, e.g. ``"INVA9999999"``).
        unpack_id : {"DESIGN", "PREDICTION"}, optional
            Which unpacking mode the server should use. Defaults to ``"PREDICTION"``.

        Returns
        -------
        list[UnpackedProductDesign]
            The unpacked composition, one entry per input formula.
        """
        url = f"{self.base_path}/{unpack_id}/unpack"
        batches = [inventory_ids[i : i + 50] for i in range(0, len(inventory_ids), 50)]
        return [
            UnpackedProductDesign(**item)
            for batch in batches
            for item in self.session.get(url, params={"formulaId": batch}).json()
        ]
