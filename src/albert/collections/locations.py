import logging
from collections.abc import Generator, Iterator

from albert.collections.base import BaseCollection
from albert.resources.locations import Location
from albert.session import AlbertSession


class LocationCollection(BaseCollection):
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

    def _list_generator(
        self,
        *,
        limit: int = 50,
        name: list[str] | str = None,
        country: str = None,
        start_key: str = None,
        exact_match: bool = False,
    ) -> Generator[Location, None, None]:
        params = {"limit": limit}
        if name:
            params["name"] = name if isinstance(name, list) else [name]
            params["exactMatch"] = str(exact_match).lower()
        if start_key:  # pragma: no cover
            params["startKey"] = start_key
        if country:
            params["country"] = country

        while True:
            response = self.session.get(self.base_path, params=params)
            loc_data = response.json().get("Items", [])
            if not loc_data or loc_data == []:
                break
            for l in loc_data:
                this_loc = Location(**l)
                yield this_loc
            start_key = response.json().get("lastKey")
            if not start_key:
                break
            params["startKey"] = start_key

    def list(
        self, *, name: str | list[str] = None, country: str = None, exact_match: bool = False
    ) -> Iterator[Location]:
        return self._list_generator(name=name, country=country, exact_match=exact_match)

    def get_by_id(self, *, id: str) -> Location | None:
        """
        Retrieves a location by its ID.

        Parameters
        ----------
        id : str
            The ID of the location to retrieve.

        Returns
        -------
        Union[Location, None]
            The Location object if found, None otherwise.
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        loc = response.json()
        found_company = Location(**loc)
        return found_company

    def update(self, *, updated_object: Location) -> Location:
        # Fetch the current object state from the server or database
        current_object = self.get_by_id(id=updated_object.id)
        # Generate the PATCH payload
        patch_payload = self._generate_patch_payload(
            existing=current_object,
            updated=updated_object,
            stringify_values=True,
        )
        url = f"{self.base_path}/{updated_object.id}"
        self.session.patch(url, json=patch_payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=updated_object.id)

    def location_exists(self, *, location: Location):
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

        payload = location.model_dump(by_alias=True, exclude_unset=True)
        response = self.session.post(self.base_path, json=payload)

        return Location(**response.json())

    def delete(self, *, location_id: str) -> None:
        """
        Deletes a Location entity.

        Parameters
        ----------
        location_id : Str
            The id of the Location object to delete.

        Returns
        -------
        None
        """
        url = f"{self.base_path}/{location_id}"
        self.session.delete(url)
