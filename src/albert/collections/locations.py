from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.resources.locations import Location


class LocationCollection(BaseCollection):
    """LocationCollection is a collection class for managing Location entities in the Albert platform."""

    _updatable_attributes = {"latitude", "longitude", "address", "country", "name"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the LocationCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{LocationCollection._api_version}/locations"

    def get_all(
        self,
        *,
        ids: list[str] | None = None,
        name: str | list[str] | None = None,
        country: str | None = None,
        exact_match: bool = False,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[Location]:
        """
        Get all Location entities matching the provided criteria.

        Parameters
        ----------
        ids : list[str], optional
            The list of IDs to filter the locations. Max length is 100.
        name : str or list[str], optional
            The name or names of locations to search for.
        country : str, optional
            Country code to filter by.
        exact_match : bool, optional
            Whether to return only exact matches. Default is False.
        start_key : str, optional
            The pagination key to start from.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[Location]
            An iterator of Location entities matching the filters.
        """
        params = {
            "startKey": start_key,
            "country": country,
        }
        if ids:
            params["id"] = ids
        if name:
            params["name"] = [name] if isinstance(name, str) else name
            params["exactMatch"] = exact_match

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [Location(**item) for item in items],
        )

    def get_by_id(self, *, id: str) -> Location:
        """
        Retrieves a location by its ID.

        Parameters
        ----------
        id : str
            The ID of the location to retrieve.

        Returns
        -------
        Location
            The Location object.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Location(**response.json())

    def update(self, *, location: Location) -> Location:
        """Update a Location entity.

        Parameters
        ----------
        location : Location
            The Location entity to update. The ID of the Location entity must be provided.

        Returns
        -------
        Location
            The updated Location entity as returned by the server.
        """
        # Fetch the current object state from the server or database
        current_object = self.get_by_id(id=location.id)
        # Generate the PATCH payload
        patch_payload = self._generate_patch_payload(
            existing=current_object,
            updated=location,
            stringify_values=True,
        )
        url = f"{self.base_path}/{location.id}"
        self.session.patch(url, json=patch_payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=location.id)

    def exists(self, *, location: Location) -> Location | None:
        """Determines if a location, with the same name, exists in the collection.

        Parameters
        ----------
        location : Location
            The Location entity to check

        Returns
        -------
        Location | None
            The existing registered Location entity if found, otherwise None.
        """
        hits = self.get_all(name=location.name)
        for hit in hits:
            if hit and hit.name.lower() == location.name.lower():
                return hit
        return None

    def create(self, *, location: Location) -> Location:
        """
        Creates a new Location entity.

        Parameters
        ----------
        location : Location
            The Location entity to create.

        Returns
        -------
        Location
            The created Location entity.
        """
        payload = location.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = self.session.post(self.base_path, json=payload)

        return Location(**response.json())

    def get_or_create(self, *, location: Location) -> Location:
        """
        Retrieves a Location by its name or creates it if it does not exist.

        Parameters
        ----------
        location : Location
            The Location entity to retrieve or create.

        Returns
        -------
        Location
            The found or created Location entity.
        """
        found = self.exists(location=location)
        if found:
            return found
        else:
            return self.create(location=location)

    def delete(self, *, id: str) -> None:
        """
        Deletes a Location entity.

        Parameters
        ----------
        id : Str
            The id of the Location entity to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)
