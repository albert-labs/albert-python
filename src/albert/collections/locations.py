import json
import logging
from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.resources.locations import Location
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


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

    def list(
        self,
        *,
        ids: list[str] | None = None,
        name: str | list[str] | None = None,
        country: str | None = None,
        exact_match: bool = False,
        limit: int = 50,
        start_key: str | None = None,
    ) -> Iterator[Location]:
        """Searches for locations matching the provided criteria.

        Parameters
        ----------
        ids: list[str] | None, optional
            The list of IDs to filter the locations, by default None.
            Max length is 100.
        name : str | list[str] | None, optional
            The name or names of locations to search for, by default None
        country : str | None, optional
            The country code of the country to filter the locations , by default None
        exact_match : bool, optional
            Whether to return exact matches only, by default False

        Yields
        ------
        Iterator[Location]
            An iterator of Location objects matching the search criteria.
        """
        params = {"limit": limit, "startKey": start_key, "country": country}
        if ids:
            params["id"] = ids
        if name:
            params["name"] = [name] if isinstance(name, str) else name
            params["exactMatch"] = json.dumps(exact_match)
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
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
            The Location object to update. The ID of the Location object must be provided.

        Returns
        -------
        Location
            The updated Location object as returned by the server.
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

    def location_exists(self, *, location: Location) -> Location | None:
        """Determines if a location, with the same name, exists in the collection.

        Parameters
        ----------
        location : Location
            The Location object to check

        Returns
        -------
        Location | None
            The existing registered Location object if found, otherwise None.
        """
        hits = self.list(name=location.name)
        if hits:
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
            The Location object to create.

        Returns
        -------
        Location
            The created Location object.
        """
        exists = self.location_exists(location=location)
        if exists:
            logging.warning(
                f"Location with name {location.name} matches an existing location. Returning the existing Location."
            )
            return exists

        payload = location.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = self.session.post(self.base_path, json=payload)

        return Location(**response.json())

    def delete(self, *, id: str) -> None:
        """
        Deletes a Location entity.

        Parameters
        ----------
        id : Str
            The id of the Location object to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)
