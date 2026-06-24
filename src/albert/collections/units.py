import logging
from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import UnitId
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.core.utils import ensure_list
from albert.resources.units import Unit, UnitCategory


class UnitCollection(BaseCollection):
    """
    UnitCollection is a collection class for managing Unit entities in the Albert platform.
    """

    _updatable_attributes = {"symbol", "synonyms", "category"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the UnitCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{UnitCollection._api_version}/units"

    def create(self, *, unit: Unit) -> Unit:
        """
        Creates a new unit entity.

        Parameters
        ----------
        unit : Unit
            The unit object to create.

        Returns
        -------
        Unit
            The created Unit object.
        """
        response = self.session.post(
            self.base_path, json=unit.model_dump(by_alias=True, exclude_unset=True, mode="json")
        )
        unit = Unit(**response.json())
        return unit

    def get_or_create(self, *, unit: Unit) -> Unit:
        """
        Retrieves a Unit or creates it if it does not exist.

        Parameters
        ----------
        unit : Unit
            The unit object to find or create.

        Returns
        -------
        Unit
            The existing or newly created Unit object.
        """
        match = self.get_by_name(name=unit.name, exact_match=True)
        if match:
            logging.warning(
                f"Unit with the name {unit.name} already exists. Returning the existing unit."
            )
            return match
        return self.create(unit=unit)

    @validate_call
    def get_by_id(self, *, id: UnitId) -> Unit:
        """
        Retrieves a unit by its ID.

        Parameters
        ----------
        id : str
            The ID of the unit to retrieve.

        Returns
        -------
        Unit
            The Unit object if found.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        this_unit = Unit(**response.json())
        return this_unit

    @validate_call
    def get_by_ids(self, *, ids: list[UnitId]) -> list[Unit]:
        """
        Retrieves a set of units by their IDs

        Parameters
        ----------
        ids : list[str]
            The IDs of the units to retrieve.

        Returns
        -------
        list[Unit]
            The Unit entities
        """
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 500] for i in range(0, len(ids), 500)]
        return [
            Unit(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()["Items"]
        ]

    @validate_call
    def update(self, *, unit: Unit) -> Unit:
        """
        Updates a unit entity by its ID.

        Parameters
        ----------
        unit : Unit
            The updated Unit object.

        Returns
        -------
        Unit
            The updated Unit

        Notes
        -----
        The following fields can be updated: ``category``, ``symbol``, ``synonyms``.
        """
        unit_id = unit.id
        original_unit = self.get_by_id(id=unit_id)
        payload = self._generate_unit_patch_payload(existing=original_unit, updated=unit)
        url = f"{self.base_path}/{unit_id}"

        # The backend rejects more than one operation on the same attribute in a
        # single request, so each Synonyms edit is sent as its own request.
        synonym_data = [d for d in payload.data if d.attribute == "Synonyms"]
        other_data = [d for d in payload.data if d.attribute != "Synonyms"]
        batches = [other_data] if other_data else []
        batches.extend([datum] for datum in synonym_data)
        for batch in batches:
            self.session.patch(
                url, json=PatchPayload(data=batch).model_dump(mode="json", by_alias=True)
            )

        unit = self.get_by_id(id=unit_id)
        return unit

    def _generate_unit_patch_payload(self, *, existing: Unit, updated: Unit) -> PatchPayload:
        """Generate patch request data for a unit, handling synonyms as item-level edits."""
        payload = self._generate_patch_payload(existing=existing, updated=updated)

        # Synonyms are added/removed one at a time; there is no list-level update,
        # so replace any whole-list datum with per-item add/delete operations.
        payload.data = [d for d in payload.data if d.attribute != "Synonyms"]
        if "synonyms" not in updated.model_fields_set:
            return payload
        existing_synonyms = existing.synonyms or []
        updated_synonyms = updated.synonyms or []
        payload.data.extend(
            PatchDatum(attribute="Synonyms", operation=PatchOperation.ADD, new_value=synonym)
            for synonym in updated_synonyms
            if synonym not in existing_synonyms
        )
        payload.data.extend(
            PatchDatum(attribute="Synonyms", operation=PatchOperation.DELETE, new_value=synonym)
            for synonym in existing_synonyms
            if synonym not in updated_synonyms
        )
        return payload

    @validate_call
    def delete(self, *, id: UnitId) -> None:
        """
        Deletes a unit by its ID.

        Parameters
        ----------
        id : str
            The ID of the unit to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    def get_all(
        self,
        *,
        name: str | list[str] | None = None,
        category: UnitCategory | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        exact_match: bool = False,
        verified: bool | None = None,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Unit]:
        """
        Get all unit entities with optional filters.

        Parameters
        ----------
        name : str | list[str] | None, optional
            The name(s) of the unit(s) to filter by.
        category : UnitCategory | None, optional
            The category of the unit to filter by.
        order_by : OrderBy, optional
            The order by which to sort the results, by default OrderBy.DESCENDING.
        exact_match : bool, optional
            Whether to match the name exactly, by default False.
        verified : bool | None, optional
            Whether the unit is verified, by default None.
        start_key : str | None, optional
            The primary key of the first item to evaluate for pagination.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[Unit]
            An iterator of Unit entities.
        """
        params = {
            "orderBy": order_by,
            "name": ensure_list(name),
            "exactMatch": exact_match,
            "verified": verified,
            "category": category,
            "startKey": start_key,
        }

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [Unit(**item) for item in items],
        )

    def get_by_name(self, *, name: str, exact_match: bool = False) -> Unit | None:
        """
        Retrieves a unit by its name.

        Parameters
        ----------
        name : str
            The name of the unit to retrieve.
        exact_match : bool, optional
            Whether to match the name exactly, by default False.

        Returns
        -------
        Optional[Unit]
            The Unit object if found, None otherwise.
        """
        found = self.get_all(name=name, exact_match=exact_match, max_items=10)
        # return the first with exactly that name
        for unit in found:
            if unit.name == name:
                return unit
        return None

    def exists(self, *, name: str, exact_match: bool = True) -> bool:
        """
        Checks if a unit exists by its name.

        Parameters
        ----------
        name : str
            The name of the unit to check.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.

        Returns
        -------
        bool
            True if the unit exists, False otherwise.
        """
        return self.get_by_name(name=name, exact_match=exact_match) is not None
