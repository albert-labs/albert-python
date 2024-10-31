import logging
from collections.abc import Generator, Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.collections.cas import Cas
from albert.collections.companies import Company, CompanyCollection
from albert.collections.tags import TagCollection
from albert.resources.inventory import InventoryCategory, InventoryItem
from albert.session import AlbertSession
from albert.utils.exceptions import ForbiddenError, NotFoundError


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
        hits = self.list(name=inventory_item.name, company=[inventory_item.company])
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
        self, *, inventory_item: InventoryItem, avoid_duplicates: bool = True
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
            json=inventory_item.model_dump(by_alias=True, exclude_none=True),
        )
        return InventoryItem(**response.json())

    def get_by_id(self, *, inventory_id: str) -> InventoryItem:
        """
        Retrieve an inventory item by its ID.

        Parameters
        ----------
        inventory_id : str
            The ID of the inventory item.

        Returns
        -------
        InventoryItem
            The retrieved inventory item.
        """
        if not inventory_id.startswith("INV"):
            inventory_id = "INV" + inventory_id
        url = f"{self.base_path}/{inventory_id}"
        response = self.session.get(url)
        return InventoryItem(**response.json())

    def get_by_ids(self, *, inventory_ids: list[str]) -> list[InventoryItem]:
        """
        Retrieve an set of inventory items by their IDs.

        Parameters
        ----------
        inventory_ids : str
            The list of IDs of the inventory items.

        Returns
        -------
        list[InventoryItem]
            The retrieved inventory items.
        """
        inventory_ids = [x if x.startswith("INV") else f"INV{x}" for x in inventory_ids]
        response = self.session.get(
            f"{self.base_path}/ids",
            params={"id": inventory_ids},
        )
        return [InventoryItem(**item) for item in response.json()["Items"]]

    def delete(self, *, inventory_id: str | InventoryItem) -> bool:
        """
        Delete an inventory item by its ID.

        Parameters
        ----------
        inventory_id : str | InventoryItem
            The ID of the inventory item.

        Returns
        -------
        None
        """
        if isinstance(inventory_id, InventoryItem):
            inventory_id = inventory_id.id
        inventory_id = inventory_id if inventory_id.startswith("INV") else "INV" + inventory_id
        url = f"{self.base_path}/{inventory_id}"
        self.session.delete(url)

    def _list_generator(
        self,
        *,
        limit: int = 25,
        offset: int | None = None,
        name: str | None = None,
        cas: list[Cas] | None = None,
        company: list[Company] | None = None,
        category: list[InventoryCategory] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
    ) -> Generator[InventoryItem, None, None]:
        """
        Generator for listing inventory items with optional filters.

        Parameters
        ----------
        limit : int, optional
            The maximum number of items to retrieve per request (default is 50).
        start_key : Optional[str], optional
            The start key for pagination.
        name : Optional[str], optional
            The name filter for the inventory items.
        cas : Optional[List[Cas]], optional
            The CAS filter for the inventory items.
        company : Optional[List[Company]], optional
            The company filter for the inventory items.
        category : Optional[List[InventoryCategory]], optional
            The category filter for the inventory items.
        order_by : OrderBy, optional
            The order in which to retrieve items (default is OrderBy.DESCENDING).

        Yields
        ------
        InventoryItem
            The next inventory item in the generator.
        """
        # Note there are other parameters we could add supprt for

        params = {
            "sortBy": "createdAt",
            "order": order_by.value,
            "limit": str(limit),
        }
        if offset:  # pragma: no cover
            params["offset"] = offset
        if name:
            params["text"] = name
        if category:
            params["category"] = [c.value for c in category]
        if cas:
            params["cas"] = [c.number for c in cas]
        if company:
            params["manufacturer"] = [c.name for c in company if isinstance(c, Company)]
        while True:
            response = self.session.get(self.base_path + "/search", params=params)
            response_data = response.json()

            raw_inventory = response_data.get("Items", [])
            start_offset = response_data.get("offset")
            params["offset"] = int(start_offset) + int(limit)
            for item in raw_inventory:
                # Unfortunetly, list only returns partial objects, so I need to do a GET on each.
                this_aid = (
                    item["albertId"]
                    if item["albertId"].startswith("INV")
                    else "INV" + item["albertId"]
                )
                try:
                    yield self.get_by_id(inventory_id=this_aid)
                except (NotFoundError, ForbiddenError):
                    # Sometimes InventoryItems are listed that the current user does not have full access to. Just skip those
                    continue
            if not raw_inventory or raw_inventory == [] or len(raw_inventory) < limit:
                break

    def list(
        self,
        *,
        name: str | None = None,
        cas: list[Cas] | Cas | None = None,
        category: list[InventoryCategory] | InventoryCategory | None = None,
        company: list[Company] | Company | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
    ) -> Iterator[InventoryItem]:
        """
        List inventory items with optional filters.

        Parameters
        ----------
        name : Optional[str], optional
            The name filter for the inventory items.
        cas : Optional[List[Cas]], optional
            The CAS filter for the inventory items.
        category : Optional[List[InventoryCategory]], optional
            The category filter for the inventory items.
        company : Optional[List[Company]], optional
            The company filter for the inventory items.
        order_by : OrderBy, optional
            The order in which to retrieve items (default is OrderBy.DESCENDING).

        Returns
        -------
        Optional[Genneraroe[InventoryItem]]
            A generator of inventory items that match the filters, or None if no items match.
        """
        # Note there are other parameters we could add supprt for

        # helpers incase the user fails to provide a list for any of these.
        if isinstance(cas, Cas):
            cas = [cas]
        if isinstance(category, InventoryCategory):
            category = [category]
        if isinstance(company, Company):
            company = [company]
        return self._list_generator(
            name=name, cas=cas, category=category, order_by=order_by, company=company
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

        _updatable_attributes_special = {"company", "tags", "cas"}
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
            elif attribute == "company":
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

            # # First handle the case where we're just adding
            # if (old_value is None or old_value == []) and new_value is not None:
            #     # company can never start as none so it's not covered in this case
            #     if attribute == "cas":
            #         for c in new_value:
            #             payload["data"].append(
            #                 {
            #                     "operation": "add",
            #                     "attribute": "casId",
            #                     "newValue": c.id,  # This will be a CasAmount Object,
            #                     "entityId": c.id,
            #                     "max": c.max,
            #                     "min": c.min,
            #                 }
            #             )
            #     elif attribute == "tags":
            #         for t in new_value:
            #             payload["data"].append(
            #                 {
            #                     "operation": "add",
            #                     "attribute": "tagId",
            #                     "newValue": t.id,  # This will be a CasAmount Object,
            #                     "entityId": t.id,
            #                 }
            #             )

            # elif old_value is not None and new_value != old_value:
            #     elif attribute == "company":
            #         if new_value is not None and new_value.id != old_value.id:
            #             # Update existing attribute
            #             payload["data"].append(
            #                 {
            #                     "operation": "update",
            #                     "attribute": "companyId",
            #                     "oldValue": old_value.id,
            #                     "newValue": new_value.id,
            #                 }
            #             )
            #     elif new_value is None:  # pragma: no cover you cant remove a company
            #         payload["data"].append(
            #             {
            #                 "operation": "delete",
            #                 "attribute": "companyId",
            #                 "entityId": old_value.id,
            #                 "oldValue": old_value.id,
            #             }
            #         )
            # elif attribute == "cas":
            #     old_cas_map = {x.id: x for x in old_value}
            #     if new_value is not None:
            #         for c in new_value:
            #             if c.id in old_cas_map:
            #                 this_old_cas = old_cas_map[c.id]
            #                 if this_old_cas.max == c.max and this_old_cas.min == c.min:
            #                     continue
            #                 if this_old_cas.max != c.max:
            #                     payload["data"].append(
            #                         {
            #                             "operation": "update",
            #                             "attribute": "max",
            #                             "entityId": c.id,
            #                             "oldValue": str(this_old_cas.max),
            #                             "newValue": str(c.max),
            #                         }
            #                     )
            #                 if this_old_cas.min != c.min:
            #                     payload["data"].append(
            #                         {
            #                             "operation": "update",
            #                             "attribute": "min",
            #                             "entityId": c.id,
            #                             "oldValue": str(this_old_cas.min),
            #                             "newValue": str(c.min),
            #                         }
            #                     )
            #             else:
            #                 payload["data"].append(
            #                     {
            #                         "operation": "add",
            #                         "attribute": "casId",
            #                         "newValue": c.id,  # This will be a CasAmount Object,
            #                         "max": c.max,
            #                         "min": c.min,
            #                     }
            #                 )
            #     for cas_id in old_cas_map:
            #         if new_value is None or cas_id not in [x.id for x in new_value]:
            #             payload["data"].append(
            #                 {
            #                     "operation": "delete",
            #                     "attribute": "casId",
            #                     "entityId": cas_id,
            #                     "oldValue": cas_id,
            #                 }
            #             )
            # elif attribute == "tags":
            #     if new_value is not None and isinstance(old_value, list):
            #         old_tag_map = {x.id: x for x in old_value}
            #         old_keys = old_tag_map.keys()
            #         new_keys = [x.id for x in new_value]
            #     else:
            #         new_keys = []
            #         new_value = []
            #     for c in new_value:
            #         if c.id in old_keys:
            #             continue
            #         else:
            #             payload["data"].append(
            #                 {
            #                     "operation": "add",
            #                     "attribute": "tagId",
            #                     "newValue": c.id,
            #                 }
            #             )
            #     for tag_id in old_keys:
            #         if tag_id not in new_keys:
            #             payload["data"].append(
            #                 {
            #                     "operation": "delete",
            #                     "attribute": "tagId",
            #                     "oldValue": tag_id,
            #                 }
            #             )
        return payload

    def update(self, *, updated_object: InventoryItem) -> InventoryItem:
        """
        Update an inventory item.

        Parameters
        ----------
        updated_object : InventoryItem
            The updated inventory item object.

        Returns
        -------
        InventoryItem
            The updated inventory item retrieved from the server.
        """
        # Fetch the current object state from the server or database
        current_object = self.get_by_id(inventory_id=updated_object.id)

        # Generate the PATCH payload
        patch_payload = self._generate_inventory_patch_payload(
            existing=current_object, updated=updated_object
        )

        # Complex patching is not working, so I'm going to do this in a loop :(
        # https://teams.microsoft.com/l/message/19:de4a48c366664ce1bafcdbea02298810@thread.tacv2/1724856117312?tenantId=98aab90e-764b-48f1-afaa-02e3c7300653&groupId=35a36a3d-fc25-4899-a1dd-ad9c7d77b5b3&parentMessageId=1724856117312&teamName=Product%20%2B%20Engineering&channelName=General%20-%20API&createdTime=1724856117312
        url = f"{self.base_path}/{updated_object.id}"
        for change in patch_payload["data"]:
            change_payload = {"data": [change]}
            self.session.patch(url, json=change_payload)
        updated_inv = self.get_by_id(inventory_id=updated_object.id)
        return updated_inv
