import logging
from collections.abc import Iterator
from typing import Any

from pydantic import TypeAdapter, validate_call

from albert.collections.base import BaseCollection
from albert.collections.cas import Cas
from albert.collections.companies import Company, CompanyCollection
from albert.collections.tags import TagCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import (
    InventoryId,
    ProjectId,
    SearchProjectId,
    WorksheetId,
)
from albert.core.utils import ensure_list
from albert.resources.facet import FacetItem
from albert.resources.inventory import (
    ALL_MERGE_MODULES,
    InventoryCategory,
    InventoryItem,
    InventoryMergeModule,
    InventorySearchItem,
    InventorySpec,
    InventorySpecList,
    MergeInventory,
)
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocation
from albert.resources.users import User
from albert.utils.inventory import _build_cas_patch_operations


class InventoryCollection(BaseCollection):
    """Manage Inventory Items in the Albert platform.

    An Inventory Item is a catalog entry for a physical or formulated material
    tracked in Albert. Every item belongs to one of four categories:

    - ``RawMaterials``: purchased substances used as ingredients (e.g. a solvent
      or pigment), typically linked to a manufacturing Company and one or more
      CAS numbers.
    - ``Consumables``: supplies consumed during lab work (e.g. gloves, vials).
    - ``Equipment``: instruments and apparatus.
    - ``Formulas``: mixtures designed in Albert. Formulas are created through the
      Worksheet collection ([`WorksheetCollection`][albert.collections.worksheets.WorksheetCollection]),
      not here; [`create`][albert.collections.inventory.InventoryCollection.create] rejects Formula items.

    Inventory Items are referenced throughout the platform by their Inventory ID
    (format ``INV...``, e.g. ``"INVA1"``). They are the building blocks that
    Worksheets, Tasks, and Property Data all point back to.

    This collection is accessed as ``client.inventory``.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.inventory import InventoryCategory
        client = Albert()
        # Find raw materials mentioning "titanium dioxide"
        items = client.inventory.get_all(
            text="titanium dioxide",
            category=InventoryCategory.RAW_MATERIALS,
            max_items=25,
        )
        for item in items:
            print(item.id, item.name)
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for inventory requests.

    Methods
    -------
    create(inventory_item, avoid_duplicates=True) -> InventoryItem
        Create a new inventory item (raw material, consumable, or equipment).
    get_by_id(id) -> InventoryItem
        Get a single fully populated item by its ID.
    get_by_ids(ids) -> list[InventoryItem]
        Get many items by their IDs in batches.
    search(...) -> Iterator[InventorySearchItem]
        Fast, lightweight search returning partial items (best for lookups/counts).
    get_all(...) -> Iterator[InventoryItem]
        Same filters as search, but returns fully populated items (slower).
    update(inventory_item) -> InventoryItem
        Update an existing item.
    delete(id) -> None
        Delete an item by its ID.
    merge(parent_id, child_id, modules=None) -> None
        Merge duplicate item(s) into a single parent item.
    exists(inventory_item) -> bool
        Check whether an item with the same name and company already exists.
    get_match_or_none(inventory_item) -> InventoryItem | None
        Return the existing item matching name + company, or None.
    add_specs(inventory_id, specs) -> InventorySpecList
        Attach specification properties to an item.
    get_specs(ids) -> list[InventorySpecList]
        Get the specs attached to a list of items.
    get_all_facets(...) -> list[FacetItem]
        Get facet groups (aggregated filter counts) for a query.
    get_facet_by_name(name, ...) -> list[FacetItem]
        Get a single named facet group for a query.
    """

    _api_version = "v3"
    _updatable_attributes = {
        "name",
        "description",
        "unit_category",
        "security_class",
        "alias",
        "is_formula_override",
        "metadata",
    }

    def __init__(self, *, session: AlbertSession):
        """Initialize an InventoryCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{InventoryCollection._api_version}/inventories"

    def _user_search_filter_values(
        self,
        value: User | str | list[User] | list[str] | None,
        *,
        user_id_only: bool = False,
    ) -> list[str] | None:
        """Serialize user search filters for inventory query params.

        ``created_by`` accepts display names or UserIds (and legacy
        [`User`][albert.resources.users.User] objects). ``updated_by`` accepts
        UserIds only on the backend; pass a UserId string or a ``User`` with
        ``id`` set.
        """
        items = ensure_list(value)
        if not items:
            return None

        wire: list[str] = []
        for item in items:
            if isinstance(item, str):
                wire.append(item)
                continue
            resolved = (item.id or item.name) if user_id_only else (item.name or item.id)
            if resolved:
                wire.append(resolved)
        return wire

    @validate_call
    def merge(
        self,
        *,
        parent_id: InventoryId,
        child_id: InventoryId | list[InventoryId],
        modules: list[InventoryMergeModule] | None = None,
    ) -> None:
        """Merge one or more duplicate inventory items into a single parent item.

        Use this to consolidate duplicates: the child item(s) are folded into the
        parent, and their data (as selected by ``modules``) is carried over. The
        child items are removed as standalone entries.

        !!! example
            ```python
            client.inventory.merge(parent_id="INVA1", child_id=["INVA2", "INVA3"])
            ```

        Parameters
        ----------
        parent_id : InventoryId
            The item to keep. All merged data ends up here.
        child_id : InventoryId or list[InventoryId]
            The duplicate item(s) to merge into the parent. At least one is required.
        modules : list[InventoryMergeModule], optional
            Which categories of data to carry over from the children (e.g. pricing,
            notes). Defaults to all modules.

        Returns
        -------
        None
        """

        # assume "all" modules if not specified explicitly
        modules = modules if modules is not None else ALL_MERGE_MODULES

        # define merge endpoint
        url = f"{self.base_path}/merge"

        child_ids = ensure_list(child_id) or []
        if not child_ids:
            raise ValueError("At least one child inventory id is required for merge operations.")
        child_inventories = [{"id": i} for i in child_ids]

        # define payload using the class
        payload = MergeInventory(
            parent_id=parent_id,
            child_inventories=child_inventories,
            modules=modules,
        )

        # post request
        self.session.post(url, json=payload.model_dump(mode="json", by_alias=True))

    def exists(self, *, inventory_item: InventoryItem) -> bool:
        """Check whether a matching inventory item already exists.

        A match is determined by name and company, the same way [`create`][albert.collections.inventory.InventoryCollection.create]
        detects duplicates. Useful before creating an item to avoid duplicates.

        !!! example
            ```python
            from albert.resources.inventory import InventoryItem, InventoryCategory
            from albert.resources.companies import Company
            candidate = InventoryItem(
                name="Acetone",
                category=InventoryCategory.RAW_MATERIALS,
                company=Company(name="Acme Chemicals"),
            )
            client.inventory.exists(inventory_item=candidate)
            # True
            ```

        Parameters
        ----------
        inventory_item : InventoryItem
            The item to look for. Its ``name`` and ``company`` are used to match.

        Returns
        -------
        bool
            True if a matching item exists, False otherwise.
        """
        hit = self.get_match_or_none(inventory_item=inventory_item)
        return bool(hit)

    def get_match_or_none(self, *, inventory_item: InventoryItem) -> InventoryItem | None:
        """Return the existing item matching name and company, or None.

        Like [`exists`][albert.collections.inventory.InventoryCollection.exists], but returns the matched item itself so you can reuse
        its ID instead of creating a duplicate.

        !!! example
            ```python
            existing = client.inventory.get_match_or_none(inventory_item=candidate)
            existing.id if existing else "no match"
            # 'INVA1'
            ```

        Parameters
        ----------
        inventory_item : InventoryItem
            The item to match. Its ``name`` and ``company`` are used to match.

        Returns
        -------
        InventoryItem or None
            The matching item, or None if no match is found.
        """
        company = inventory_item.company
        company_id = company.id if company is not None else None
        company_name = company.name if company is not None else None

        hits = self.get_all(
            text=inventory_item.name,
            company=[company] if isinstance(company, Company) else None,
            max_items=100,
        )

        for inv in hits:
            if inv.name != inventory_item.name:
                continue
            inv_company = inv.company
            # Prefer matching on company id; fall back to name when the id is
            # unavailable (e.g. an unsaved Company passed without an id).
            if company_id is not None:
                matched = inv_company is not None and inv_company.id == company_id
            else:
                matched = (inv_company.name if inv_company else None) == company_name
            if matched:
                return inv
        return None

    def create(
        self,
        *,
        inventory_item: InventoryItem,
        avoid_duplicates: bool = True,
    ) -> InventoryItem:
        """Create a new inventory item.

        Use this to add a raw material, consumable, or equipment item to the
        catalog. Formula items are not supported here; build those through the
        Worksheet collection.

        Any tags or company on the item that do not yet exist in Albert are
        created automatically before the item is registered (see
        [`CompanyCollection`][albert.collections.companies.CompanyCollection] and
        [`TagCollection`][albert.collections.tags.TagCollection]).

        !!! example
            ```python
            from albert.resources.inventory import InventoryItem, InventoryCategory
            from albert.resources.companies import Company
            item = InventoryItem(
                name="Titanium Dioxide",
                category=InventoryCategory.RAW_MATERIALS,
                company=Company(name="Acme Chemicals"),
            )
            created = client.inventory.create(inventory_item=item)
            created.id
            # 'INVA1'
            ```

        Parameters
        ----------
        inventory_item : InventoryItem
            The item to create. ``name`` and ``category`` are required. For raw
            materials, set ``company`` to the manufacturing Company and ``cas`` to
            the relevant CAS numbers.
        avoid_duplicates : bool, optional
            When True (default), if an item with the same name and company already
            exists, that existing item is returned instead of creating a duplicate.
            Set to False to force creation.

        Returns
        -------
        InventoryItem
            The newly created item, populated with its assigned Inventory ID.

        Raises
        ------
        NotImplementedError
            If ``inventory_item.category`` is ``Formulas``.
        """
        category = (
            inventory_item.category
            if isinstance(inventory_item.category, str)
            else inventory_item.category.value
        )
        if category == InventoryCategory.FORMULAS.value:
            # This will need to interact with worksheets
            raise NotImplementedError("Registrations of formulas not yet implemented")
        tag_collection = TagCollection(session=self.session)
        if inventory_item.tags is not None and inventory_item.tags != []:
            all_tags = [
                tag_collection.get_or_create(tag=t) if t.id is None else t
                for t in inventory_item.tags
            ]
            inventory_item.tags = all_tags
        if inventory_item.company and inventory_item.company.id is None:
            company_collection = CompanyCollection(session=self.session)
            inventory_item.company = company_collection.get_or_create(
                company=inventory_item.company
            )
        # Check to see if there is a match on name + Company already
        if avoid_duplicates:
            existing = self.get_match_or_none(inventory_item=inventory_item)
            if isinstance(existing, InventoryItem):
                logging.warning(
                    f"Inventory item already exists with name {existing.name} and company {existing.company.name}, returning existing item."
                )
                return existing
        response = self.session.post(
            self.base_path,
            json=inventory_item.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )

        # ACL is populated after the create response is sent by the API.
        return self.get_by_id(id=response.json()["albertId"])

    @validate_call
    def get_by_id(self, *, id: InventoryId) -> InventoryItem:
        """Get a single, fully populated inventory item by its ID.

        For retrieving many items at once, use [`get_by_ids`][albert.collections.inventory.InventoryCollection.get_by_ids]. To find items
        without knowing their IDs, use [`search`][albert.collections.inventory.InventoryCollection.search] or [`get_all`][albert.collections.inventory.InventoryCollection.get_all].

        !!! example
            ```python
            item = client.inventory.get_by_id(id="INVA1")
            item.name
            # 'Titanium Dioxide'
            ```

        Parameters
        ----------
        id : InventoryId
            The Inventory ID (format ``INV...``, e.g. ``"INVA1"``).

        Returns
        -------
        InventoryItem
            The fully populated item.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return InventoryItem(**response.json())

    @validate_call
    def get_by_ids(self, *, ids: list[InventoryId]) -> list[InventoryItem]:
        """Get multiple fully populated inventory items by their IDs.

        Requests are automatically split into batches, so arbitrarily long ID
        lists are supported. Items not found are omitted from the result.

        !!! example
            ```python
            items = client.inventory.get_by_ids(ids=["INVA1", "INVA2"])
            [i.name for i in items]
            # ['Titanium Dioxide', 'Acetone']
            ```

        Parameters
        ----------
        ids : list[InventoryId]
            The Inventory IDs to retrieve (format ``INV...``).

        Returns
        -------
        list[InventoryItem]
            The matching items. Order is not guaranteed to match the input.
        """
        batch_size = 250
        batches = [ids[i : i + batch_size] for i in range(0, len(ids), batch_size)]
        inventory = []
        for batch in batches:
            response = self.session.get(f"{self.base_path}/ids", params={"id": batch})
            inventory.extend([InventoryItem(**item) for item in response.json()["Items"]])
        return inventory

    @validate_call
    def get_specs(self, *, ids: list[InventoryId]) -> list[InventorySpecList]:
        """Get the specs attached to a list of inventory items.

        A spec is a declared property of an item (see [`add_specs`][albert.collections.inventory.InventoryCollection.add_specs] for the
        distinction between specs and task-measured Property Data). Requests are
        automatically batched.

        !!! example
            ```python
            spec_lists = client.inventory.get_specs(ids=["INVA1"])
            spec_lists[0].specs
            # [...]
            ```

        Parameters
        ----------
        ids : list[InventoryId]
            The Inventory IDs to fetch specs for (format ``INV...``).

        Returns
        -------
        list[InventorySpecList]
            One entry per item, each holding that item's specs.
        """
        url = f"{self.base_path}/specs"
        batches = [ids[i : i + 250] for i in range(0, len(ids), 250)]
        ta = TypeAdapter(InventorySpecList)
        return [
            ta.validate_python(item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()
        ]

    @validate_call
    def add_specs(
        self,
        *,
        inventory_id: InventoryId,
        specs: InventorySpec | list[InventorySpec],
    ) -> InventorySpecList:
        """Attach one or more specs to an inventory item.

        An ``InventorySpec`` is a declared property of an item, as opposed to a
        value measured through a Task. Use specs for generic, known properties
        (e.g. a supplier-stated density); use Tasks and Property Data for
        experimentally measured results. A spec can optionally carry the
        conditions under which it holds, expressed via a workflow.

        !!! example
            ```python
            from albert.resources.inventory import InventorySpec, InventorySpecValue
            spec = InventorySpec(
                name="Density",
                data_column_id="DAC1",
                value=InventorySpecValue(min="1.1", max="1.3"),
            )
            client.inventory.add_specs(inventory_id="INVA1", specs=spec)
            ```

        Parameters
        ----------
        inventory_id : InventoryId
            The item to attach the specs to (format ``INV...``).
        specs : InventorySpec or list[InventorySpec]
            The spec(s) to attach. Each describes a value and, optionally, the
            associated conditions (via workflow).

        Returns
        -------
        InventorySpecList
            The full set of specs now attached to the item.
        """
        if isinstance(specs, InventorySpec):
            specs = [specs]
        response = self.session.put(
            url=f"{self.base_path}/{inventory_id}/specs",
            json=[x.model_dump(exclude_unset=True, by_alias=True, mode="json") for x in specs],
        )
        return InventorySpecList(**response.json())

    @validate_call
    def delete(self, *, id: InventoryId) -> None:
        """Delete an inventory item by its ID.

        This permanently removes the item. To consolidate duplicates while
        preserving data, use [`merge`][albert.collections.inventory.InventoryCollection.merge] instead.

        !!! example
            ```python
            client.inventory.delete(id="INVA1")
            ```

        Parameters
        ----------
        id : InventoryId
            The Inventory ID to delete (format ``INV...``).

        Returns
        -------
        None
        """

        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    @validate_call
    def _prepare_parameters(
        self,
        *,
        text: str | None = None,
        cas: list[Cas] | Cas | None = None,
        category: list[InventoryCategory] | InventoryCategory | None = None,
        company: list[Company] | Company | None = None,
        order: OrderBy | None = None,
        sort_by: str | None = None,
        location: list[Location] | Location | None = None,
        storage_location: list[StorageLocation] | StorageLocation | None = None,
        project_id: SearchProjectId | None = None,
        sheet_id: WorksheetId | None = None,
        created_by: list[User] | User | str | list[str] | None = None,
        lot_owner: list[User] | User | None = None,
        tags: list[str] | None = None,
        offset: int | None = None,
        from_created_at: str | None = None,
        to_created_at: str | None = None,
        updated_by: list[User] | User | str | list[str] | None = None,
        from_updated_at: str | None = None,
        to_updated_at: str | None = None,
    ):
        if isinstance(cas, Cas):
            cas = [cas]
        if isinstance(category, InventoryCategory):
            category = [category]
        if isinstance(company, Company):
            company = [company]
        if isinstance(lot_owner, User):
            lot_owner = [lot_owner]
        if isinstance(location, Location):
            location = [location]
        if isinstance(storage_location, StorageLocation):
            storage_location = [storage_location]

        params = {
            "text": text,
            "order": order,
            "sortBy": sort_by if sort_by is not None else None,
            "category": category,
            "tags": tags,
            "manufacturer": [c.name for c in company] if company is not None else None,
            "cas": [c.number for c in cas] if cas is not None else None,
            "location": [c.name for c in location] if location is not None else None,
            "storageLocation": (
                [c.name for c in storage_location] if storage_location is not None else None
            ),
            "lotOwner": [c.name for c in lot_owner] if lot_owner is not None else None,
            "createdBy": self._user_search_filter_values(created_by),
            "sheetId": sheet_id,
            "projectId": project_id,
            "offset": offset,
            "fromCreatedAt": from_created_at if from_created_at is not None else None,
            "toCreatedAt": to_created_at if to_created_at is not None else None,
            "updatedBy": self._user_search_filter_values(updated_by, user_id_only=True),
            "fromUpdatedAt": from_updated_at if from_updated_at is not None else None,
            "toUpdatedAt": to_updated_at if to_updated_at is not None else None,
        }

        return params

    @validate_call
    def get_all_facets(
        self,
        *,
        text: str | None = None,
        cas: list[Cas] | Cas | None = None,
        category: list[InventoryCategory] | InventoryCategory | None = None,
        company: list[Company] | Company | None = None,
        location: list[Location] | Location | None = None,
        storage_location: list[StorageLocation] | StorageLocation | None = None,
        project_id: ProjectId | None = None,
        sheet_id: WorksheetId | None = None,
        created_by: list[User] | User | str | list[str] | None = None,
        lot_owner: list[User] | User | None = None,
        tags: list[str] | None = None,
        match_all_conditions: bool = False,
    ) -> list[FacetItem]:
        """Get the facets available for an inventory search.

        Facets are the grouped, counted filter options for a query, like the
        refinement sidebar of a search UI (e.g. how many matching items fall under
        each category, company, or tag). Use them to build progressive filtering
        or to summarize a result set without fetching every item. To pull a single
        named facet, use [`get_facet_by_name`][albert.collections.inventory.InventoryCollection.get_facet_by_name].

        !!! example
            ```python
            facets = client.inventory.get_all_facets(text="titanium dioxide")
            [f.name for f in facets]
            # ['Category', 'Company', 'Tags', ...]
            ```

        Parameters
        ----------
        text : str, optional
            Free-text query matched against item name and related fields.
        cas : Cas or list[Cas], optional
            Filter by CAS number(s).
        category : InventoryCategory or list[InventoryCategory], optional
            Filter by category: ``RawMaterials``, ``Consumables``, ``Equipment``,
            or ``Formulas``.
        company : Company or list[Company], optional
            Filter by manufacturing Company.
        location : Location or list[Location], optional
            Filter by location.
        storage_location : StorageLocation or list[StorageLocation], optional
            Filter by storage location.
        project_id : ProjectId, optional
            Filter by project.
        sheet_id : WorksheetId, optional
            Filter by worksheet.
        created_by : User, list[User], str, or list[str], optional
            Filter by creator. Accepts user display name(s) or UserId(s) (e.g.
            ``"USR4227"`` or ``"Jane Doe"``), or [`User`][albert.resources.users.User]
            object(s).
        lot_owner : User or list[User], optional
            Filter by lot owner.
        tags : list[str], optional
            Filter by tag name(s).
        match_all_conditions : bool, optional
            If True, only count items that satisfy every applied filter (AND logic).
            Default False.

        Returns
        -------
        list[FacetItem]
            The facet groups available for the query.
        """

        params = self._prepare_parameters(
            text=text,
            cas=cas,
            category=category,
            company=company,
            location=location,
            storage_location=storage_location,
            project_id=project_id,
            sheet_id=sheet_id,
            created_by=created_by,
            lot_owner=lot_owner,
            tags=tags,
        )
        params["limit"] = 1
        params = {k: v for k, v in params.items() if v is not None}
        response = self.session.get(
            url=f"{self.base_path}/llmsearch"
            if match_all_conditions
            else f"{self.base_path}/search",
            params=params,
        )
        return [FacetItem.model_validate(x) for x in response.json()["Facets"]]

    @validate_call
    def get_facet_by_name(
        self,
        name: str | list[str],
        *,
        text: str | None = None,
        cas: list[Cas] | Cas | None = None,
        category: list[InventoryCategory] | InventoryCategory | None = None,
        company: list[Company] | Company | None = None,
        location: list[Location] | Location | None = None,
        storage_location: list[StorageLocation] | StorageLocation | None = None,
        project_id: ProjectId | None = None,
        sheet_id: WorksheetId | None = None,
        created_by: list[User] | User | str | list[str] | None = None,
        lot_owner: list[User] | User | None = None,
        tags: list[str] | None = None,
        match_all_conditions: bool = False,
    ) -> list[FacetItem]:
        """Return one or more named facets for an inventory search.

        A convenience wrapper over [`get_all_facets`][albert.collections.inventory.InventoryCollection.get_all_facets] that keeps only the
        facet group(s) you name. Useful for iterative search refinement, e.g.
        fetching the remaining ``Tags`` facet after other filters are applied.

        !!! example
            ```python
            tags = client.inventory.get_facet_by_name("Tags", text="acetone")
            tags[0].name
            # 'Tags'
            ```

        Parameters
        ----------
        name : str or list[str]
            The facet group name(s) to return (e.g. ``"Tags"``, ``"Company"``).
            Matching is case-insensitive.
        text : str, optional
            Search text for full-text matching.
        cas : list[Cas] | Cas | None, optional
            Filter by CAS values.
        category : list[InventoryCategory] | InventoryCategory | None, optional
            Filter by inventory category.
        company : list[Company] | Company | None, optional
            Filter by company.
        location : list[Location] | Location | None, optional
            Filter by location.
        storage_location : list[StorageLocation] | StorageLocation | None, optional
            Filter by storage location.
        project_id : ProjectId | None, optional
            Filter by project.
        sheet_id : WorksheetId | None, optional
            Filter by worksheet.
        created_by : User, list[User], str, or list[str], optional
            Filter by creator. Accepts user display name(s) or UserId(s) (e.g.
            ``"USR4227"`` or ``"Jane Doe"``), or [`User`][albert.resources.users.User]
            object(s).
        lot_owner : list[User] | User | None, optional
            Filter by lot owner.
        tags : list[str] | None, optional
            Filter by tags.
        match_all_conditions : bool, optional
            If True, only count items that satisfy every applied filter (AND logic).
            Default False.

        Returns
        -------
        list[FacetItem]
            The facet group(s) matching ``name``.
        """
        name = ensure_list(name) or []

        facets = self.get_all_facets(
            text=text,
            cas=cas,
            category=category,
            company=company,
            location=location,
            storage_location=storage_location,
            project_id=project_id,
            sheet_id=sheet_id,
            created_by=created_by,
            lot_owner=lot_owner,
            tags=tags,
            match_all_conditions=match_all_conditions,
        )
        filtered_facets = []
        for facet in facets:
            if facet.name in name or facet.name.lower() in name:
                filtered_facets.append(facet)

        return filtered_facets

    @validate_call
    def search(
        self,
        *,
        text: str | None = None,
        cas: list[Cas] | Cas | None = None,
        category: list[InventoryCategory] | InventoryCategory | None = None,
        company: list[Company] | Company | None = None,
        location: list[Location] | Location | None = None,
        storage_location: list[StorageLocation] | StorageLocation | None = None,
        project_id: ProjectId | None = None,
        sheet_id: WorksheetId | None = None,
        created_by: list[User] | User | str | list[str] | None = None,
        lot_owner: list[User] | User | None = None,
        tags: list[str] | None = None,
        match_all_conditions: bool = False,
        order: OrderBy = OrderBy.DESCENDING,
        sort_by: str | None = None,
        max_items: int | None = None,
        offset: int | None = 0,
        from_created_at: str | None = None,
        to_created_at: str | None = None,
        updated_by: list[User] | User | str | list[str] | None = None,
        from_updated_at: str | None = None,
        to_updated_at: str | None = None,
        metadata_filters: dict[str, Any] | None = None,
    ) -> Iterator[InventorySearchItem]:
        """Search for inventory items matching the given filters.

        Returns lightweight, partially populated results and is the fastest way to
        look items up (best for name lookups, counts, or feeding IDs into another
        call). Fields such as full CAS breakdowns and metadata are omitted; when
        you need complete items, use [`get_all`][albert.collections.inventory.InventoryCollection.get_all] with the same filters, or pass
        the resulting IDs to [`get_by_ids`][albert.collections.inventory.InventoryCollection.get_by_ids].

        Filters are combined with OR logic by default (an item matches if it
        satisfies any filter); set ``match_all_conditions=True`` to require every
        filter to match. Results are returned as a lazily paginated iterator, so
        iterating fetches additional pages on demand.

        !!! example
            ```python
            from albert.resources.inventory import InventoryCategory
            hits = client.inventory.search(
                text="acetone",
                category=InventoryCategory.RAW_MATERIALS,
                max_items=10,
            )
            first = next(iter(hits))
            first.name
            # 'Acetone'
            ```

        Parameters
        ----------
        text : str, optional
            Free-text query matched against item name, alias, and related fields.
            Only the first 50 characters are used.
        cas : Cas or list[Cas], optional
            Filter by CAS number(s).
        category : InventoryCategory or list[InventoryCategory], optional
            Filter by category: ``RawMaterials``, ``Consumables``, ``Equipment``,
            or ``Formulas``.
        company : Company or list[Company], optional
            Filter by manufacturing Company.
        location : Location or list[Location], optional
            Filter by location.
        storage_location : StorageLocation or list[StorageLocation], optional
            Filter by storage location.
        project_id : str, optional
            Filter by the project a formula belongs to (Formula items only).
        sheet_id : str, optional
            Filter by worksheet ID.
        created_by : User, list[User], str, or list[str], optional
            Filter by creator. Accepts user display name(s) or UserId(s) (e.g.
            ``"USR4227"`` or ``"Jane Doe"``), or [`User`][albert.resources.users.User]
            object(s).
        lot_owner : User or list[User], optional
            Filter by lot owner(s).
        tags : list[str], optional
            Filter by tag name(s).
        match_all_conditions : bool, optional
            Require every filter to match (AND logic). Default False (OR logic).
        order : OrderBy, optional
            Sort direction. Default ``OrderBy.DESCENDING``.
        sort_by : str, optional
            Field to sort by. Default None (server default order).
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.
        from_created_at : str, optional
            Only include items created on or after this date, formatted as
            ``YYYY-MM-DD``.
        to_created_at : str, optional
            Only include items created on or before this date, formatted as
            ``YYYY-MM-DD``.
        updated_by : User, list[User], str, or list[str], optional
            Filter by user(s) who last updated the item. Accepts UserId(s) only
            (e.g. ``"USR4227"``), not display names. Pass a UserId string, or a
            [`User`][albert.resources.users.User] with ``id`` set.
        from_updated_at : str, optional
            Only include items updated on or after this date (ISO 8601).
        to_updated_at : str, optional
            Only include items updated on or before this date (ISO 8601).
        metadata_filters : dict[str, Any], optional
            Filters for custom field values, sent in the ``metadataFilters`` request
            body field. When set, the search uses POST instead of GET.

        Returns
        -------
        Iterator[InventorySearchItem]
            A lazily paginated iterator of partially populated search results.
        """

        def deserialize(items: list[dict]):
            return [InventorySearchItem.model_validate(x)._bind_collection(self) for x in items]

        search_text = text if (text is None or len(text) < 50) else text[:50]

        query_params = self._prepare_parameters(
            text=search_text,
            cas=cas,
            category=category,
            company=company,
            order=order,
            sort_by=sort_by,
            location=location,
            storage_location=storage_location,
            project_id=project_id,
            sheet_id=sheet_id,
            created_by=created_by,
            lot_owner=lot_owner,
            tags=tags,
            offset=offset,
            from_created_at=from_created_at,
            to_created_at=to_created_at,
            updated_by=updated_by,
            from_updated_at=from_updated_at,
            to_updated_at=to_updated_at,
        )

        path = (
            f"{self.base_path}/llmsearch" if match_all_conditions else f"{self.base_path}/search"
        )

        if metadata_filters is not None:
            payload: dict[str, Any] = {
                **query_params,
                "metadataFilters": {"metadata": metadata_filters},
            }
            return AlbertPaginator(
                mode=PaginationMode.OFFSET,
                path=path,
                session=self.session,
                max_items=max_items,
                deserialize=deserialize,
                method="POST",
                json=payload,
            )

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=path,
            params=query_params,
            session=self.session,
            max_items=max_items,
            deserialize=deserialize,
        )

    @validate_call
    def get_all(
        self,
        *,
        text: str | None = None,
        cas: list[Cas] | Cas | None = None,
        category: list[InventoryCategory] | InventoryCategory | None = None,
        company: list[Company] | Company | None = None,
        location: list[Location] | Location | None = None,
        storage_location: list[StorageLocation] | StorageLocation | None = None,
        project_id: ProjectId | None = None,
        sheet_id: WorksheetId | None = None,
        created_by: list[User] | User | str | list[str] | None = None,
        lot_owner: list[User] | User | None = None,
        tags: list[str] | None = None,
        match_all_conditions: bool = False,
        order: OrderBy = OrderBy.DESCENDING,
        sort_by: str | None = None,
        max_items: int | None = None,
        offset: int | None = 0,
        from_created_at: str | None = None,
        to_created_at: str | None = None,
        updated_by: list[User] | User | str | list[str] | None = None,
        from_updated_at: str | None = None,
        to_updated_at: str | None = None,
        metadata_filters: dict[str, Any] | None = None,
    ) -> Iterator[InventoryItem]:
        """Get fully populated inventory items matching the given filters.

        Accepts the same filters as [`search`][albert.collections.inventory.InventoryCollection.search] but returns complete
        ``InventoryItem`` entities rather than lightweight search results. This is
        slower because it fetches full detail for every match, so prefer
        [`search`][albert.collections.inventory.InventoryCollection.search] when you only need names, IDs, or counts.

        Filters are combined with OR logic by default; set
        ``match_all_conditions=True`` to require every filter to match. Results are
        returned as a lazily paginated iterator.

        !!! example
            ```python
            from albert.resources.inventory import InventoryCategory
            for item in client.inventory.get_all(
                category=InventoryCategory.RAW_MATERIALS,
                max_items=50,
            ):
                print(item.id, item.name)
            ```

        Parameters
        ----------
        text : str, optional
            Free-text query matched against item name, alias, and related fields.
            Only the first 50 characters are used.
        cas : Cas or list[Cas], optional
            Filter by CAS number(s).
        category : InventoryCategory or list[InventoryCategory], optional
            Filter by category: ``RawMaterials``, ``Consumables``, ``Equipment``,
            or ``Formulas``.
        company : Company or list[Company], optional
            Filter by manufacturing Company.
        location : Location or list[Location], optional
            Filter by location.
        storage_location : StorageLocation or list[StorageLocation], optional
            Filter by storage location.
        project_id : str, optional
            Filter by the project a formula belongs to (Formula items only).
        sheet_id : str, optional
            Filter by worksheet ID.
        created_by : User, list[User], str, or list[str], optional
            Filter by creator. Accepts user display name(s) or UserId(s) (e.g.
            ``"USR4227"`` or ``"Jane Doe"``), or [`User`][albert.resources.users.User]
            object(s).
        lot_owner : User or list[User], optional
            Filter by lot owner(s).
        tags : list[str], optional
            Filter by tag name(s).
        match_all_conditions : bool, optional
            Require every filter to match (AND logic). Default False (OR logic).
        order : OrderBy, optional
            Sort direction. Default ``OrderBy.DESCENDING``.
        sort_by : str, optional
            Field to sort by. Default None (server default order).
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.
        from_created_at : str, optional
            Only include items created on or after this date, formatted as
            ``YYYY-MM-DD``.
        to_created_at : str, optional
            Only include items created on or before this date, formatted as
            ``YYYY-MM-DD``.
        updated_by : User, list[User], str, or list[str], optional
            Filter by user(s) who last updated the item. Accepts UserId(s) only
            (e.g. ``"USR4227"``), not display names. Pass a UserId string, or a
            [`User`][albert.resources.users.User] with ``id`` set.
        from_updated_at : str, optional
            Only include items updated on or after this date (ISO 8601).
        to_updated_at : str, optional
            Only include items updated on or before this date (ISO 8601).
        metadata_filters : dict[str, Any], optional
            Filters for custom field values, sent in the ``metadataFilters`` request
            body field. When set, the search uses POST instead of GET.

        Returns
        -------
        Iterator[InventoryItem]
            A lazily paginated iterator of fully populated items.
        """

        def deserialize(items: list[dict]) -> list[InventoryItem]:
            return self.get_by_ids(ids=[x["albertId"] for x in items])

        search_text = text if (text is None or len(text) < 50) else text[:50]

        query_params = self._prepare_parameters(
            text=search_text,
            cas=cas,
            category=category,
            company=company,
            order=order,
            sort_by=sort_by,
            location=location,
            storage_location=storage_location,
            project_id=project_id,
            sheet_id=sheet_id,
            created_by=created_by,
            lot_owner=lot_owner,
            tags=tags,
            offset=offset,
            from_created_at=from_created_at,
            to_created_at=to_created_at,
            updated_by=updated_by,
            from_updated_at=from_updated_at,
            to_updated_at=to_updated_at,
        )

        path = (
            f"{self.base_path}/llmsearch" if match_all_conditions else f"{self.base_path}/search"
        )

        if metadata_filters is not None:
            payload: dict[str, Any] = {
                **query_params,
                "metadataFilters": {"metadata": metadata_filters},
            }
            return AlbertPaginator(
                mode=PaginationMode.OFFSET,
                path=path,
                session=self.session,
                max_items=max_items,
                deserialize=deserialize,
                method="POST",
                json=payload,
            )

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=path,
            params=query_params,
            session=self.session,
            max_items=max_items,
            deserialize=deserialize,
        )

    def _generate_inventory_patch_payload(
        self, *, existing: InventoryItem, updated: InventoryItem
    ) -> dict:
        """
        Generate PATCH request data for updating an inventory item.

        Parameters
        ----------
        existing : BaseAlbertModel
            The existing state of the inventory item.
        updated : BaseAlbertModel
            The updated state of the inventory item.

        Returns
        -------
        dict
            Request data for the PATCH operation.
        """

        def _remove_old_value_on_add(patch_dict):
            if "oldValue" in patch_dict and patch_dict["operation"] == "add":
                del patch_dict["oldValue"]
            return patch_dict

        _updatable_attributes_special = {"company", "tags", "cas", "acls"}
        payload = self._generate_patch_payload(existing=existing, updated=updated)
        payload = payload.model_dump(mode="json", by_alias=True)
        if (
            existing.category == InventoryCategory.FORMULAS
            and updated.is_formula_override is not None
        ):
            payload["data"] = self._normalize_formula_override_patch(
                payload["data"], updated.is_formula_override
            )
        for attribute in _updatable_attributes_special:
            if attribute not in updated.model_fields_set:
                continue
            old_value = getattr(existing, attribute)
            new_value = getattr(updated, attribute)
            if attribute == "cas":
                cas_operations = _build_cas_patch_operations(existing=old_value, updated=new_value)
                payload["data"].extend(cas_operations)
            elif attribute == "acls":
                existing_ids = [x.id for x in existing.acls]
                new_ids = [x.id for x in updated.acls]
                to_add = set(new_ids) - set(existing_ids)
                to_del = set(existing_ids) - set(new_ids)
                to_update = set(existing_ids).intersection(new_ids)
                if len(to_add) > 0:
                    payload["data"].append(
                        {
                            "attribute": "ACL",
                            "operation": "add",
                            "newValue": [
                                x.model_dump(by_alias=True) for x in updated.acls if x.id in to_add
                            ],
                        },
                    )
                if len(to_del) > 0:
                    payload["data"].append(
                        {
                            "attribute": "ACL",
                            "operation": "delete",
                            "oldValue": [
                                x.model_dump(by_alias=True)
                                for x in existing.acls
                                if x.id in to_del
                            ],
                        },
                    )
                for acl_id in to_update:
                    existing_fgc = [x.fgc for x in existing.acls if x.id == acl_id][0]
                    updated_fgc = [x.fgc for x in updated.acls if x.id == acl_id][0]
                    if existing_fgc != updated_fgc:
                        payload["data"].append(
                            {
                                "attribute": "fgc",
                                "id": acl_id,
                                "operation": "update",
                                "oldValue": existing_fgc.value,
                                "newValue": updated_fgc.value,
                            },
                        )

            elif attribute == "tags":
                if (old_value is None or old_value == []) and new_value is not None:
                    for t in new_value:
                        payload["data"].append(
                            {
                                "operation": "add",
                                "attribute": "tagId",
                                "newValue": t.id,  # This will be a CasAmount Object,
                                "entityId": t.id,
                            }
                        )
                else:
                    if old_value is None:  # pragma: no cover
                        old_value = []
                    if new_value is None:  # pragma: no cover
                        new_value = []
                    old_set = {obj.id for obj in old_value}
                    new_set = {obj.id for obj in new_value}

                    # Find what's in set 1 but not in set 2
                    to_del = old_set - new_set

                    # Find what's in set 2 but not in set 1
                    to_add = new_set - old_set

                    for id in to_add:
                        payload["data"].append(
                            {
                                "operation": "add",
                                "attribute": "tagId",
                                "newValue": id,
                            }
                        )
                    for id in to_del:
                        payload["data"].append(
                            {
                                "operation": "delete",
                                "attribute": "tagId",
                                "oldValue": id,
                            }
                        )
            elif attribute == "company" and old_value is not None or new_value is not None:
                if old_value is None and new_value is not None:
                    payload["data"].append(
                        {
                            "operation": "add",
                            "attribute": "companyId",
                            "newValue": new_value.id,
                        }
                    )
                elif old_value is not None and new_value is None:
                    payload["data"].append(
                        {"operation": "delete", "attribute": "companyId", "entityId": old_value.id}
                    )
                elif old_value.id != new_value.id:
                    payload["data"].append(
                        {
                            "operation": "update",
                            "attribute": "companyId",
                            "oldValue": old_value.id,
                            "newValue": new_value.id,
                        }
                    )
        return payload

    @staticmethod
    def _normalize_formula_override_patch(
        patch_data: list[dict], is_formula_override: bool
    ) -> list[dict]:
        for change in list(patch_data):
            if change.get("attribute") != "isFormulaOverride":
                continue
            if change.get("operation") != "add":
                return patch_data
            if is_formula_override is False:
                patch_data.remove(change)
                return patch_data
            change["operation"] = "update"
            change["oldValue"] = False
            return patch_data
        return patch_data

    def update(self, *, inventory_item: InventoryItem) -> InventoryItem:
        """Update an existing inventory item.

        Fetch the item (e.g. with [`get_by_id`][albert.collections.inventory.InventoryCollection.get_by_id]), modify the updatable fields
        on the returned object, then pass it here. Only the fields listed in Notes
        are applied; changes to other fields are ignored.

        !!! example
            ```python
            item = client.inventory.get_by_id(id="INVA1")
            item.description = "Updated description"
            updated = client.inventory.update(inventory_item=item)
            updated.description
            # 'Updated description'
            ```

        Parameters
        ----------
        inventory_item : InventoryItem
            The item to update. Must have a valid ``id``.

        Returns
        -------
        InventoryItem
            The updated item.

        Notes
        -----
        The following fields can be updated: ``alias``, ``description``,
        ``is_formula_override``, ``metadata``, ``name``, ``security_class``,
        ``unit_category``.
        """
        # Fetch the current object state from the server or database
        current_object = self.get_by_id(id=inventory_item.id)
        # Generate the PATCH payload
        patch_payload = self._generate_inventory_patch_payload(
            existing=current_object, updated=inventory_item
        )

        # Complex patching does not work for some fields, so I'm going to do this in a loop :(
        # https://teams.microsoft.com/l/message/19:de4a48c366664ce1bafcdbea02298810@thread.tacv2/1724856117312?tenantId=98aab90e-764b-48f1-afaa-02e3c7300653&groupId=35a36a3d-fc25-4899-a1dd-ad9c7d77b5b3&parentMessageId=1724856117312&teamName=Product%20%2B%20Engineering&channelName=General%20-%20API&createdTime=1724856117312
        url = f"{self.base_path}/{inventory_item.id}"
        batch_patch_changes = list()
        for change in patch_payload["data"]:
            if change["attribute"].startswith("Metadata."):  # Metadata can be batch patched
                batch_patch_changes.append(change)
            else:
                change_payload = {"data": [change]}
                self.session.patch(url, json=change_payload)

        # Use batch update for fields that allow it
        if batch_patch_changes:
            batch_patch_payload = {"data": batch_patch_changes}
            self.session.patch(url, json=batch_patch_payload)

        updated_inv = self.get_by_id(id=inventory_item.id)
        return updated_inv
