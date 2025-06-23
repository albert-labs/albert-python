import logging
from collections.abc import Iterator

from pydantic import TypeAdapter, validate_call

from albert.collections.base import BaseCollection, OrderBy
from albert.collections.cas import Cas
from albert.collections.companies import Company, CompanyCollection
from albert.collections.tags import TagCollection
from albert.resources.facet import FacetItem
from albert.resources.identifiers import InventoryId, ProjectId, SearchProjectId, WorksheetId
from albert.resources.inventory import (
    ALL_MERGE_MODULES,
    InventoryCategory,
    InventoryItem,
    InventorySearchItem,
    InventorySpec,
    InventorySpecList,
    MergeInventory,
)
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocation
from albert.resources.users import User
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class InventoryCollection(BaseCollection):
    """InventoryCollection is a collection class for managing Inventory Item entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {
        "name",
        "description",
        "unit_category",
        "security_class",
        "alias",
        "metadata",
    }

    def __init__(self, *, session: AlbertSession):
        """
        InventoryCollection is a collection class for managing inventory items.

        Parameters
        ----------
        session : Albert
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{InventoryCollection._api_version}/inventories"

    def merge(
        self,
        *,
        parent_id: InventoryId,
        child_id: InventoryId | list[InventoryId],
        modules: list[str] | None = None,
    ) -> None:
        """
        Merge one or multiple child inventory into a parent inventory item.

        Parameters
        ----------
        parent_id : InventoryId
            The ID of the parent inventory item.
        child_id : InventoryId | list[InventoryId]
            The ID(s) of the child inventory item(s).
        modules : list[str], optional
            The merge modules to use (default is all).

        Returns
        -------
        None
        """

        # assume "all" modules if not specified explicitly
        modules = modules if modules is not None else ALL_MERGE_MODULES

        # define merge endpoint
        url = f"{self.base_path}/merge"

        if isinstance(child_id, list):
            child_inventories = [{"id": i} for i in child_id]
        else:
            child_inventories = [{"id": child_id}]

        # define payload using the class
        payload = MergeInventory(
            parent_id=parent_id,
            child_inventories=child_inventories,
            modules=modules,
        )

        # post request
        self.session.post(url, json=payload.model_dump(mode="json", by_alias=True))

    def inventory_exists(self, *, inventory_item: InventoryItem) -> bool:
        """
        Check if an inventory item exists.

        Parameters
        ----------
        inventory_item : InventoryItem
            The inventory item to check.

        Returns
        -------
        bool
            True if the inventory item exists, False otherwise.
        """
        hit = self.get_match_or_none(inventory_item=inventory_item)
        return bool(hit)

    def get_match_or_none(self, *, inventory_item: InventoryItem) -> InventoryItem | None:
        """
        Get a matching inventory item or return None if not found.

        Parameters
        ----------
        inventory_item : InventoryItem
            The inventory item to match.

        Returns
        -------
        Union[InventoryItem, None]
            The matching inventory item or None if not found.
        """
        hits = self.list(text=inventory_item.name, company=[inventory_item.company])
        inv_company = (
            inventory_item.company.name
            if isinstance(inventory_item.company, Company)
            else inventory_item.company
        )
        for inv in hits:
            if inv and inv.name == inventory_item.name and inv.company.name == inv_company:
                return inv
        else:
            return None

    def create(
        self,
        *,
        inventory_item: InventoryItem,
        avoid_duplicates: bool = True,
    ) -> InventoryItem:
        """
        Create a new inventory item.

        Parameters
        ----------
        inventory_item : InventoryItem
            The inventory item to create.
        avoid_duplicates : bool, optional
            Whether to avoid creating duplicate items (default is True).

        Returns
        -------
        InventoryItem
            The created inventory item.
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
                tag_collection.create(tag=t) if t.id is None else t for t in inventory_item.tags
            ]
            inventory_item.tags = all_tags
        if inventory_item.company and inventory_item.company.id is None:
            company_collection = CompanyCollection(session=self.session)
            inventory_item.company = company_collection.create(company=inventory_item.company)
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
        return InventoryItem(**response.json())

    @validate_call
    def get_by_id(self, *, id: InventoryId) -> InventoryItem:
        """
        Retrieve an inventory item by its ID.

        Parameters
        ----------
        id : InventoryId
            The ID of the inventory item.

        Returns
        -------
        InventoryItem
            The retrieved inventory item.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return InventoryItem(**response.json())

    @validate_call
    def get_by_ids(self, *, ids: list[InventoryId]) -> list[InventoryItem]:
        """
        Retrieve an set of inventory items by their IDs.

        Parameters
        ----------
        ids : list[InventoryId]
            The list of IDs of the inventory items.

        Returns
        -------
        list[InventoryItem]
            The retrieved inventory items.
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
        """Get the specs for a list of inventory items.

        Parameters
        ----------
        ids : list[InventoryId]
            List of Inventory IDs to get the specs for.

        Returns
        -------
        list[InventorySpecList]
            A list of InventorySpecList objects, each containing the specs for an inventory item.
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
        """Add inventory specs to the inventory item.

        An `InventorySpec` is a property that was not directly measured via a task,
        but is a generic property of that inentory item.

        Parameters
        ----------
        inventory_id : InventoryId
            The Albert ID of the inventory item to add the specs to
        specs : list[InventorySpec]
            List of InventorySpec objects to add to the inventory item,
            which described the value and, optionally,
            the conditions associated with the value (via workflow).

        Returns
        -------
        InventorySpecList
            The list of InventorySpecs attached to the InventoryItem.
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
        """
        Delete an inventory item by its ID.

        Parameters
        ----------
        id : InventoryId
            The ID of the inventory item.

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
        limit: int | None = None,
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
        created_by: list[User] | User | None = None,
        lot_owner: list[User] | User | None = None,
        tags: list[str] | None = None,
    ):
        if isinstance(cas, Cas):
            cas = [cas]
        if isinstance(category, InventoryCategory):
            category = [category]
        if isinstance(company, Company):
            company = [company]
        if isinstance(lot_owner, User):
            lot_owner = [lot_owner]
        if isinstance(created_by, User):
            created_by = [created_by]
        if isinstance(location, Location):
            location = [location]
        if isinstance(storage_location, StorageLocation):
            storage_location = [storage_location]

        params = {
            "limit": limit,
            "text": text,
            "order": order.value if order is not None else None,
            "sortBy": sort_by if sort_by is not None else None,
            "category": [c.value for c in category] if category is not None else None,
            "tags": tags,
            "manufacturer": [c.name for c in company] if company is not None else None,
            "cas": [c.number for c in cas] if cas is not None else None,
            "location": [c.name for c in location] if location is not None else None,
            "storageLocation": (
                [c.name for c in storage_location] if storage_location is not None else None
            ),
            "lotOwner": [c.name for c in lot_owner] if lot_owner is not None else None,
            "createdBy": [c.name for c in created_by] if created_by is not None else None,
            "sheetId": sheet_id,
            "projectId": project_id,
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
        created_by: list[User] | User | None = None,
        lot_owner: list[User] | User | None = None,
        tags: list[str] | None = None,
        match_all_conditions: bool = False,
    ) -> list[FacetItem]:
        """
        Get available facets for inventory items based on the provided filters.
        """

        params = self._prepare_parameters(
            limit=1,
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
        created_by: list[User] | User | None = None,
        lot_owner: list[User] | User | None = None,
        tags: list[str] | None = None,
        match_all_conditions: bool = False,
    ) -> list[FacetItem]:
        """
        Returns a specific facet by its name with all the filters applied to the search.
        This can be used for example to fetch all remaining tags as part of an iterative
        refinement of a search.
        """
        if isinstance(name, str):
            name = [name]

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
        limit: int = 100,
        text: str | None = None,
        cas: list[Cas] | Cas | None = None,
        category: list[InventoryCategory] | InventoryCategory | None = None,
        company: list[Company] | Company | None = None,
        location: list[Location] | Location | None = None,
        storage_location: list[StorageLocation] | StorageLocation | None = None,
        project_id: ProjectId | None = None,
        sheet_id: WorksheetId | None = None,
        created_by: list[User] | User | None = None,
        lot_owner: list[User] | User | None = None,
        tags: list[str] | None = None,
        match_all_conditions: bool = False,
    ) -> Iterator[InventorySearchItem]:
        """
        Get a list of inventory items that match the search criteria and
        return the raw search records. These are not full inventory item
        objects, but are special short documents intended for fast summary results
        """

        def deserialize(items: list[dict]):
            return [InventorySearchItem.model_validate(x) for x in items]

        params = self._prepare_parameters(
            limit=limit,
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
        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/llmsearch"
            if match_all_conditions
            else f"{self.base_path}/search",
            params=params,
            session=self.session,
            deserialize=deserialize,
        )

    @validate_call
    def list(
        self,
        *,
        limit: int = 100,
        text: str | None = None,
        cas: list[Cas] | Cas | None = None,
        category: list[InventoryCategory] | InventoryCategory | None = None,
        company: list[Company] | Company | None = None,
        order: OrderBy = OrderBy.DESCENDING,
        sort_by: str | None = "createdAt",
        location: list[Location] | Location | None = None,
        storage_location: list[StorageLocation] | StorageLocation | None = None,
        project_id: ProjectId | None = None,
        sheet_id: WorksheetId | None = None,
        created_by: list[User] | User | None = None,
        lot_owner: list[User] | User | None = None,
        tags: list[str] | None = None,
        match_all_conditions: bool = False,
    ) -> Iterator[InventoryItem]:
        """
        List inventory items with optional filters.

        Parameters
        ----------
        limit : int, optional
            Maximum number of items to return (default is 100)
        text : str, optional
            Text to search for in inventory names and descriptions
        cas : list[Cas] | Cas | None, optional
            Filter by CAS number(s)
        category : list[InventoryCategory] | InventoryCategory | None, optional
            Filter by inventory category/categories
        company : list[Company] | Company | None, optional
            Filter by manufacturing company/companies
        order : OrderBy, optional
            Sort order, either ASCENDING or DESCENDING (default is DESCENDING)
        sort_by : str, optional
            Field to sort by (default is "createdAt")
        location : list[Location] | None, optional
            Filter by location(s)
        storage_location : list[StorageLocation] | None, optional
            Filter by storage location(s)
        project_id : str, optional
            Filter by project ID
        sheet_id : str, optional
            Filter by sheet ID
        created_by : list[User], optional
            Filter by creator(s)
        lot_owner : list[User], optional
            Filter by lot owner(s)
        tags : list[str], optional
            Filter by tag(s)
        match_all_conditions : bool, optional
            Whether to match all conditions (default is False -- e.g. OR between conditions)

        Returns
        -------
        Iterator[InventoryItem]
            An iterator over the matching inventory items
        """

        def deserialize(items: list[dict]) -> list[InventoryItem]:
            return self.get_by_ids(ids=[x["albertId"] for x in items])

        search_text = text if (text is None or len(text) < 50) else text[0:50]
        params = self._prepare_parameters(
            limit=limit,
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
        )
        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/llmsearch"
            if match_all_conditions
            else f"{self.base_path}/search",
            params=params,
            session=self.session,
            deserialize=deserialize,
        )

    def _generate_inventory_patch_payload(
        self, *, existing: InventoryItem, updated: InventoryItem
    ) -> dict:
        """
        Generate the PATCH payload for updating an inventory item.

        Parameters
        ----------
        existing : BaseAlbertModel
            The existing state of the inventory item.
        updated : BaseAlbertModel
            The updated state of the inventory item.

        Returns
        -------
        dict
            The payload for the PATCH request.
        """

        def _remove_old_value_on_add(patch_dict):
            if "oldValue" in patch_dict and patch_dict["operation"] == "add":
                del patch_dict["oldValue"]
            return patch_dict

        _updatable_attributes_special = {"company", "tags", "cas", "acls"}
        payload = self._generate_patch_payload(existing=existing, updated=updated)
        payload = payload.model_dump(mode="json", by_alias=True)
        for attribute in _updatable_attributes_special:
            old_value = getattr(existing, attribute)
            new_value = getattr(updated, attribute)
            if attribute == "cas":
                if (old_value is None or old_value == []) and new_value is not None:
                    for c in new_value:
                        payload["data"].append(
                            {
                                "operation": "add",
                                "attribute": "casId",
                                "newValue": c.id,  # This will be a CasAmount Object,
                                "entityId": c.id,
                                "max": c.max,
                                "min": c.min,
                            }
                        )
                else:
                    # Get the IDs from both sets
                    old_set = set() if old_value is None else {obj.id for obj in old_value}
                    new_set = set() if new_value is None else {obj.id for obj in new_value}
                    old_lookup = (
                        dict() if old_value is None else {obj.id: obj for obj in old_value}
                    )
                    new_lookup = (
                        dict() if new_value is None else {obj.id: obj for obj in new_value}
                    )

                    # Find what's in set 1 but not in set 2
                    to_del = old_set - new_set

                    # Find what's in set 2 but not in set 1
                    to_add = new_set - old_set

                    to_check_for_update = old_set.intersection(new_set)

                    for id in to_add:
                        add_payload = {
                            "operation": "add",
                            "attribute": "casId",
                            "newValue": new_lookup[id].id,
                            "max": new_lookup[id].max,
                            "min": new_lookup[id].min,
                            "inventoryValue": new_lookup[id].target,
                            "casCategory": new_lookup[id].cas_category,
                        }
                        add_payload = {k: v for k, v in add_payload.items() if v is not None}
                        payload["data"].append(add_payload)
                    for id in to_del:
                        payload["data"].append(
                            {
                                "operation": "delete",
                                "attribute": "casId",
                                "entityId": id,
                                "oldValue": id,
                            }
                        )
                    for id in to_check_for_update:
                        if old_lookup[id].max != new_lookup[id].max:
                            if new_lookup[id].max is not None:
                                payload["data"].append(
                                    _remove_old_value_on_add(
                                        {
                                            "operation": "update"
                                            if old_lookup[id].max is not None
                                            else "add",
                                            "attribute": "max",
                                            "entityId": id,
                                            "oldValue": str(old_lookup[id].max),
                                            "newValue": str(new_lookup[id].max),
                                        }
                                    )
                                )
                            else:
                                payload["data"].append(
                                    {
                                        "operation": "delete",
                                        "attribute": "max",
                                        "entityId": id,
                                        "oldValue": str(old_lookup[id].max),
                                    }
                                )
                        if old_lookup[id].min != new_lookup[id].min:
                            if new_lookup[id].min is not None:
                                payload["data"].append(
                                    _remove_old_value_on_add(
                                        {
                                            "operation": "update"
                                            if old_lookup[id].min is not None
                                            else "add",
                                            "attribute": "min",
                                            "entityId": id,
                                            "oldValue": str(old_lookup[id].min),
                                            "newValue": str(new_lookup[id].min),
                                        }
                                    )
                                )
                            else:
                                payload["data"].append(
                                    {
                                        "operation": "delete",
                                        "attribute": "min",
                                        "entityId": id,
                                        "oldValue": str(old_lookup[id].min),
                                    }
                                )
                        if old_lookup[id].target != new_lookup[id].target:
                            if new_lookup[id].target is not None:
                                payload["data"].append(
                                    _remove_old_value_on_add(
                                        {
                                            "operation": "update"
                                            if old_lookup[id].target is not None
                                            else "add",
                                            "attribute": "inventoryValue",
                                            "entityId": id,
                                            "oldValue": str(old_lookup[id].target),
                                            "newValue": str(new_lookup[id].target),
                                        }
                                    )
                                )
                            else:
                                payload["data"].append(
                                    {
                                        "operation": "delete",
                                        "attribute": "inventoryValue",
                                        "entityId": id,
                                        "oldValue": str(old_lookup[id].target),
                                    }
                                )
                        if old_lookup[id].cas_category != new_lookup[id].cas_category:
                            if new_lookup[id].cas_category is not None:
                                payload["data"].append(
                                    _remove_old_value_on_add(
                                        {
                                            "operation": "update"
                                            if old_lookup[id].cas_category is not None
                                            else "add",
                                            "attribute": "casCategory",
                                            "entityId": id,
                                            "oldValue": str(old_lookup[id].cas_category),
                                            "newValue": str(new_lookup[id].cas_category),
                                        }
                                    )
                                )
                            else:
                                payload["data"].append(
                                    {
                                        "operation": "delete",
                                        "attribute": "casCategory",
                                        "entityId": id,
                                        "oldValue": str(old_lookup[id].cas_category),
                                    }
                                )

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

    def update(self, *, inventory_item: InventoryItem) -> InventoryItem:
        """
        Update an inventory item.

        Parameters
        ----------
        inventory_item : InventoryItem
            The updated inventory item object.

        Returns
        -------
        InventoryItem
            The updated inventory item retrieved from the server.
        """
        # Fetch the current object state from the server or database
        current_object = self.get_by_id(id=inventory_item.id)

        # Generate the PATCH payload
        patch_payload = self._generate_inventory_patch_payload(
            existing=current_object, updated=inventory_item
        )

        # Complex patching is not working, so I'm going to do this in a loop :(
        # https://teams.microsoft.com/l/message/19:de4a48c366664ce1bafcdbea02298810@thread.tacv2/1724856117312?tenantId=98aab90e-764b-48f1-afaa-02e3c7300653&groupId=35a36a3d-fc25-4899-a1dd-ad9c7d77b5b3&parentMessageId=1724856117312&teamName=Product%20%2B%20Engineering&channelName=General%20-%20API&createdTime=1724856117312
        url = f"{self.base_path}/{inventory_item.id}"
        for change in patch_payload["data"]:
            change_payload = {"data": [change]}
            self.session.patch(url, json=change_payload)
        updated_inv = self.get_by_id(id=inventory_item.id)
        return updated_inv
