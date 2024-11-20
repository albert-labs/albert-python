import json
import logging

from albert.collections.base import BaseCollection
from albert.resources.locations import Location
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


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

    def list(
        self,
        *,
        limit: int = 50,
        name: str | list[str] | None = None,
        country: str | None = None,
        start_key: str | None = None,
        exact_match: bool = False,
    ) -> AlbertPaginator[Location]:
        params = {"limit": limit, "startKey": start_key, "country": country}
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
