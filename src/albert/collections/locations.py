from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.utils import ensure_list
from albert.resources.locations import Location


class LocationCollection(BaseCollection):
    """Manage Locations in the Albert platform.

    A Location is a physical lab or site (for example, a building, plant, or
    campus) where work happens in Albert. Locations are referenced by Tasks and
    by Inventory Items to record where an activity is performed or where a
    material lives, and each Location can hold one or more Storage Locations
    ([`StorageLocation`][albert.resources.storage_locations.StorageLocation]).

    This collection is accessed as ``client.locations``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for location requests.

    Methods
    -------
    create(location) -> Location
        Register a new location.
    get_by_id(id) -> Location
        Retrieve a single location by its Albert ID.
    get_all(...) -> Iterator[Location]
        Iterate over locations, optionally filtered by name or country.
    update(location) -> Location
        Apply changes to an existing location.
    exists(location) -> Location | None
        Return the existing location matching the given name, or None.
    get_or_create(location) -> Location
        Return the matching location if it exists, otherwise create it.
    delete(id) -> None
        Delete a location by its Albert ID.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        for location in client.locations.get_all(country="US"):
            print(location.id, location.name)
        ```
    """

    _updatable_attributes = {"latitude", "longitude", "address", "country", "name"}
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize the LocationCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
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
        """Iterate over Locations, optionally filtered by name or country.

        Results are yielded lazily and pagination is handled automatically.

        Parameters
        ----------
        ids : list[str], optional
            Restrict results to these Albert location IDs. Maximum of 100.
        name : str or list[str], optional
            One or more location names to search for.
        country : str, optional
            Two-letter country code to filter by (for example, ``"US"``).
        exact_match : bool, optional
            If True, match ``name`` exactly instead of as a substring.
            Default is False.
        start_key : str, optional
            Pagination key to resume iteration from a previous page.
        max_items : int, optional
            Maximum number of locations to return in total. If None, all
            matching locations are returned.

        Returns
        -------
        Iterator[Location]
            Locations matching the given filters.

        !!! example
            ```python
            for location in client.locations.get_all(name="Boston Lab"):
                print(location.id, location.name)
            ```
        """
        params = {
            "startKey": start_key,
            "country": country,
        }
        if ids:
            params["id"] = ids
        params["name"] = ensure_list(name)
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
        """Retrieve a single Location by its Albert ID.

        Parameters
        ----------
        id : str
            The Albert ID of the location to retrieve.

        Returns
        -------
        Location
            The fully populated location.

        !!! example
            ```python
            location = client.locations.get_by_id(id="...")
            print(location.name)
            ```
        """
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return Location(**response.json())

    def update(self, *, location: Location) -> Location:
        """Apply changes to an existing Location.

        Fetches the current server state, computes the difference against the
        supplied location, and applies it.

        Parameters
        ----------
        location : Location
            The location to update. Its ``id`` must be set.

        Returns
        -------
        Location
            The updated location as returned by the server.

        Notes
        -----
        The following fields can be updated: ``address``, ``country``,
        ``latitude``, ``longitude``, ``name``.

        !!! example
            ```python
            location = client.locations.get_by_id(id="...")
            location.name = "Boston Lab (Bldg 2)"
            updated = client.locations.update(location=location)
            ```
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
        """Return the existing Location matching the given name, or None.

        The match is case-insensitive on ``name``. Useful before creating a
        location to avoid duplicates.

        Parameters
        ----------
        location : Location
            The location to look for. Its ``name`` is used to match.

        Returns
        -------
        Location or None
            The matching registered location, or None if no match is found.

        !!! example
            ```python
            from albert.resources.locations import Location
            candidate = Location(
                name="Boston Lab",
                latitude=42.3601,
                longitude=-71.0589,
                address="1 Main St",
                country="US",
            )
            existing = client.locations.exists(location=candidate)
            ```
        """
        hits = self.get_all(name=location.name)
        for hit in hits:
            if hit and hit.name.lower() == location.name.lower():
                return hit
        return None

    def create(self, *, location: Location) -> Location:
        """Register a new Location.

        Parameters
        ----------
        location : Location
            The location to create.

        Returns
        -------
        Location
            The newly created location, populated with its assigned ``id``.

        !!! example
            ```python
            from albert.resources.locations import Location
            location = client.locations.create(
                location=Location(
                    name="Boston Lab",
                    latitude=42.3601,
                    longitude=-71.0589,
                    address="1 Main St",
                    country="US",
                )
            )
            ```
        """
        payload = location.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = self.session.post(self.base_path, json=payload)

        return Location(**response.json())

    def get_or_create(self, *, location: Location) -> Location:
        """Return the matching Location if it exists, otherwise create it.

        Looks for an existing location with the same name (see [`exists`][albert.collections.locations.LocationCollection.exists])
        and returns it; if none is found, creates the location.

        Parameters
        ----------
        location : Location
            The location to retrieve or create.

        Returns
        -------
        Location
            The existing or newly created location.

        !!! example
            ```python
            from albert.resources.locations import Location
            location = client.locations.get_or_create(
                location=Location(
                    name="Boston Lab",
                    latitude=42.3601,
                    longitude=-71.0589,
                    address="1 Main St",
                    country="US",
                )
            )
            ```
        """
        found = self.exists(location=location)
        if found:
            return found
        else:
            return self.create(location=location)

    def delete(self, *, id: str) -> None:
        """Delete a Location by its Albert ID.

        Parameters
        ----------
        id : str
            The Albert ID of the location to delete.

        Returns
        -------
        None

        !!! example
            ```python
            client.locations.delete(id="...")
            ```
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)
