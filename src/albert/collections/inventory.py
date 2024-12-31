import logging
from collections.abc import Iterator

from pydantic import TypeAdapter

from albert.collections.base import BaseCollection, OrderBy
from albert.collections.cas import Cas
from albert.collections.companies import Company, CompanyCollection
from albert.collections.tags import TagCollection
from albert.resources.inventory import (
    InventoryCategory,
    InventoryItem,
    InventorySpec,
    InventorySpecList,
)
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocation
from albert.resources.users import User
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class InventoryCollection(BaseCollection):
    """
    InventoryCollection is a collection class for managing inventory items.

    Parameters
    ----------
    session : Albert
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base URL for inventory API requests.

    Methods
    -------
    create(inventory_item: InventoryItem, avoid_duplicates: bool = True) -> InventoryItem
        Creates a new inventory item.
    get_by_id(inventory_id: str) -> Optional[InventoryItem]
        Retrieves an inventory item by its ID.
    update(inventory_id: str, patch_data: dict) -> bool
        Updates an inventory item by its ID.
    delete(inventory_id: str) -> bool
        Deletes an inventory item by its ID.
    list(limit: int, start_key: Optional[str], name: Optional[List[str]], category: Optional[str], order_by: OrderBy, exact_match: bool) -> Optional[List[InventoryItem]]
        Lists inventory items with optional filters.
    """

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
        super().__init__(session=session)
        self.base_path = f"/api/{InventoryCollection._api_version}/inventories"

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

    def get_by_id(self, *, id: str) -> InventoryItem:
        """
        Retrieve an inventory item by its ID.

        Parameters
        ----------
        id : str
            The ID of the inventory item.

        Returns
        -------
        InventoryItem
            The retrieved inventory item.
        """
        if not id.startswith("INV"):
            id = "INV" + id
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return InventoryItem(**response.json())

    def get_by_ids(self, *, ids: list[str]) -> list[InventoryItem]:
        """
        Retrieve an set of inventory items by their IDs.

        Parameters
        ----------
        ids : str
            The list of IDs of the inventory items.

        Returns
        -------
        list[InventoryItem]
            The retrieved inventory items.
        """
        url = f"{self.base_path}/ids"
        ids = [x if x.startswith("INV") else f"INV{x}" for x in ids]
        batches = [ids[i : i + 250] for i in range(0, len(ids), 250)]
        return [
            InventoryItem(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()["Items"]
        ]

    def get_specs(self, *, ids: list[str]) -> list[InventorySpecList]:
        url = f"{self.base_path}/specs"
        ids = [x if x.startswith("INV") else f"INV{x}" for x in ids]
        batches = [ids[i : i + 250] for i in range(0, len(ids), 250)]
        ta = TypeAdapter(InventorySpecList)
        return [
            ta.validate_python(item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()
        ]

    def add_specs(
        self,
        *,
        inventory_id: str,
        specs: InventorySpec | list[InventorySpec],
    ) -> InventorySpecList:
        """Add inventory specs to the inventory item.

        An `InventorySpec` is a property that was not directly measured via a task,
        but is a generic property of that inentory item.

        Parameters
        ----------
        inventory_id : str
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
        if not inventory_id.startswith("INV"):
            inventory_id = f"INV{inventory_id}"
        if isinstance(specs, InventorySpec):
            specs = [specs]
        response = self.session.put(
            url=f"{self.base_path}/{inventory_id}/specs",
            json=[x.model_dump(exclude_unset=True, by_alias=True, mode="json") for x in specs],
        )
        return InventorySpecList(**response.json())

    def delete(self, *, id: str) -> None:
        """
        Delete an inventory item by its ID.

        Parameters
        ----------
        id : str
            The ID of the inventory item.

        Returns
        -------
        None
        """
        if isinstance(id, InventoryItem):
            id = id.id
        id = id if id.startswith("INV") else "INV" + id
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

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
        location: list[Location] | None = None,
        storage_location: list[StorageLocation] | None = None,
        project_id: str | None = None,
        sheet_id: str | None = None,
        created_by: list[User] = None,
        lot_owner: list[User] = None,
        tags: list[str] = None,
    ) -> Iterator[InventoryItem]:
        """
        List inventory items with optional filters.
        """

        def deserialize(items: list[dict]) -> list[InventoryItem]:
            return self.get_by_ids(ids=[x["albertId"] for x in items])

        # Note there are other parameters we could add supprt for

        # helpers incase the user fails to provide a list for any of these.
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
        if project_id is not None and project_id.startswith("PRO"):
            project_id = project_id[3:]  # this search doesnt use the prefix

        params = {
            "limit": limit,
            "text": text,
            "order": order.value,
            "sortBy": sort_by,
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

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
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
                        payload["data"].append(
                            {
                                "operation": "add",
                                "attribute": "casId",
                                "newValue": new_lookup[id].id,
                                "max": new_lookup[id].max,
                                "min": new_lookup[id].min,
                            }
                        )
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
                            payload["data"].append(
                                {
                                    "operation": "update",
                                    "attribute": "max",
                                    "entityId": id,
                                    "oldValue": str(old_lookup[id].max),
                                    "newValue": str(new_lookup[id].max),
                                }
                            )
                        if old_lookup[id].min != new_lookup[id].min:
                            payload["data"].append(
                                {
                                    "operation": "update",
                                    "attribute": "min",
                                    "entityId": id,
                                    "oldValue": str(old_lookup[id].min),
                                    "newValue": str(new_lookup[id].min),
                                }
                            )

            elif attribute == "acls":
                if old_value and new_value and new_value != old_value:
                    payload["data"].append(
                        {
                            "operation": "update",
                            "attribute": "ACL",
                            "oldValue": [x.model_dump(by_alias=True) for x in old_value],
                            "newValue": [x.model_dump(by_alias=True) for x in new_value],
                        }
                    )
                elif new_value:
                    payload["data"].append(
                        {
                            "operation": "add",
                            "attribute": "ACL",
                            "newValue": [x.model_dump(by_alias=True) for x in new_value],
                        }
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
