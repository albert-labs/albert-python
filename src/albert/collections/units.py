import json
import logging
from collections.abc import Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.units import Unit, UnitCategory
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


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
        hit = self.get_by_name(name=unit.name, exact_match=True)
        if hit is not None:
            logging.warning(
                f"Unit with the name {hit.name} already exists. Returning the existing unit."
            )
            return hit
        response = self.session.post(
            self.base_path, json=unit.model_dump(by_alias=True, exclude_unset=True, mode="json")
        )
        this_unit = Unit(**response.json())
        return this_unit

    def get_by_id(self, *, id: str) -> Unit:
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

    def get_by_ids(self, *, ids: list[str]) -> list[Unit]:
        """
        Retrieves a set of units by their IDs

        Parameters
        ----------
        ids : list[str]
            The IDs of the units to retrieve.

        Returns
        -------
        list[Unit]
            The Unit objects
        """
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 500] for i in range(0, len(ids), 500)]
        return [
            Unit(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()["Items"]
        ]

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
        """
        unit_id = unit.id
        original_unit = self.get_by_id(id=unit_id)
        payload = self._generate_patch_payload(existing=original_unit, updated=unit)
        url = f"{self.base_path}/{unit_id}"
        self.session.patch(url, json=payload.model_dump(mode="json", by_alias=True))
        unit = self.get_by_id(id=unit_id)
        return unit

    def delete(self, *, id: str) -> None:
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

    def list(
        self,
        *,
        limit: int = 100,
        name: str | list[str] | None = None,
        category: UnitCategory | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        exact_match: bool = False,
        start_key: str | None = None,
        verified: bool | None = None,
    ) -> Iterator[Unit]:
        """
        Lists unit entities with optional filters.

        Parameters
        ----------
        limit : int, optional
            The maximum number of units to return, by default 50.
        name : Optional[str], optional
            The name of the unit to filter by, by default None.
        category : Optional[UnitCategory], optional
            The category of the unit to filter by, by default None.
        order_by : OrderBy, optional
            The order by which to sort the results, by default OrderBy.DESCENDING.
        exact_match : bool, optional
            Whether to match the name exactly, by default False.
        start_key : Optional[str], optional
            The starting point for the next set of results, by default None.

        Returns
        -------
        Iterator[Unit]
            An iterator of Unit objects.
        """
        params = {
            "limit": limit,
            "startKey": start_key,
            "orderBy": order_by.value,
            "name": [name] if isinstance(name, str) else name,
            "exactMatch": json.dumps(exact_match),
            "verified": json.dumps(verified) if verified is not None else None,
            "category": category.value if isinstance(category, UnitCategory) else category,
        }
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
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
        found = self.list(name=name, exact_match=exact_match)
        return next(found, None)

    def unit_exists(self, *, name: str, exact_match: bool = True) -> bool:
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
