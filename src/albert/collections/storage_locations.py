import logging
from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.models.base import EntityLink
from albert.core.utils import ensure_list
from albert.exceptions import AlbertHTTPError
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocation


class StorageLocationsCollection(BaseCollection):
    """Manage Storage Locations in the Albert platform.

    A Storage Location is a specific place where an Inventory Item is physically
    kept, such as a flammables cabinet, freezer, or storeroom shelf. Every
    Storage Location belongs to a parent Location
    ([`Location`][albert.resources.locations.Location]), and Inventory search filters
    can narrow results to items held in a given Storage Location.

    Storage Location IDs use the format ``STL...`` (for example, ``"STL1"``).

    This collection is accessed as ``client.storage_locations``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for storage location requests.

    Methods
    -------
    create(storage_location) -> StorageLocation
        Create a new storage location.
    get_by_id(id) -> StorageLocation
        Get a single storage location by its Albert ID.
    get_all(...) -> Iterator[StorageLocation]
        Iterate over storage locations, optionally filtered by name or location.
    update(storage_location) -> StorageLocation
        Update an existing storage location.
    get_or_create(storage_location) -> StorageLocation
        Return the matching storage location if it exists, otherwise create it.
    delete(id) -> None
        Delete a storage location by its Albert ID.

    Examples
    --------
    ```python
    from albert import Albert
    client = Albert()
    for storage_location in client.storage_locations.get_all(name="Freezer A"):
        print(storage_location.id, storage_location.name)
    ```
    """

    _api_version = "v3"
    _updatable_attributes = {"name"}

    def __init__(self, *, session: AlbertSession):
        """Initialize a StorageLocationsCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{StorageLocationsCollection._api_version}/storagelocations"

    def get_by_id(self, *, id: str) -> StorageLocation:
        """Get a single Storage Location by its Albert ID.

        Parameters
        ----------
        id : str
            The Albert ID of the storage location to retrieve (format ``STL...``).

        Returns
        -------
        StorageLocation
            The fully populated storage location.

        Examples
        --------
        ```python
        storage_location = client.storage_locations.get_by_id(id="STL1")
        print(storage_location.name)
        ```
        """
        path = f"{self.base_path}/{id}"
        response = self.session.get(path)
        return StorageLocation(**response.json())

    def get_all(
        self,
        *,
        name: str | list[str] | None = None,
        exact_match: bool = False,
        location: str | Location | None = None,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[StorageLocation]:
        """Iterate over Storage Locations, optionally filtered by name or location.

        Results are yielded lazily and pagination is handled automatically.

        Parameters
        ----------
        name : str or list[str], optional
            One or more storage location names to filter by.
        exact_match : bool, optional
            If True, match ``name`` exactly instead of as a substring.
            Default is False.
        location : str or Location, optional
            Restrict results to a parent Location, given either as a location ID
            or a [`Location`][albert.resources.locations.Location] object.
        start_key : str, optional
            Pagination key to resume iteration from a previous page.
        max_items : int, optional
            Maximum number of storage locations to return in total. If None, all
            matching storage locations are returned.

        Returns
        -------
        Iterator[StorageLocation]
            Storage locations matching the given filters.

        Examples
        --------
        ```python
        for storage_location in client.storage_locations.get_all(
            location="...",
        ):
            print(storage_location.id, storage_location.name)
        ```
        """

        # Remove explicit hydration when SUP-410 is fixed
        def deserialize(items: list[dict]) -> Iterator[StorageLocation]:
            for x in items:
                id = x["albertId"]
                try:
                    yield self.get_by_id(id=id)
                except AlbertHTTPError as e:
                    logger.warning(f"Error fetching storage location {id}: {e}")

        params = {
            "locationId": location.id
            if isinstance(location, (Location | EntityLink))
            else location,
            "startKey": start_key,
        }

        params["name"] = ensure_list(name)
        params["exactMatch"] = exact_match

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=deserialize,
        )

    def create(self, *, storage_location: StorageLocation) -> StorageLocation:
        """Create a new Storage Location.

        Parameters
        ----------
        storage_location : StorageLocation
            The storage location to create. Its ``name`` and parent ``location``
            are required.

        Returns
        -------
        StorageLocation
            The newly created storage location, populated with its assigned ``id``.

        Examples
        --------
        ```python
        from albert.resources.locations import Location
        from albert.resources.storage_locations import StorageLocation
        parent = client.locations.get_by_id(id="...")
        storage_location = client.storage_locations.create(
            storage_location=StorageLocation(name="Freezer A", location=parent)
        )
        ```
        """
        response = self.session.post(
            self.base_path,
            json=storage_location.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return StorageLocation(**response.json())

    def get_or_create(self, *, storage_location: StorageLocation) -> StorageLocation:
        """Return the matching Storage Location if it exists, otherwise create it.

        Looks for an existing storage location with the same name under the same
        parent Location (case-insensitive) and returns it; if none is found,
        creates the storage location.

        Parameters
        ----------
        storage_location : StorageLocation
            The storage location to retrieve or create.

        Returns
        -------
        StorageLocation
            The existing or newly created storage location.

        Examples
        --------
        ```python
        from albert.resources.storage_locations import StorageLocation
        parent = client.locations.get_by_id(id="...")
        storage_location = client.storage_locations.get_or_create(
            storage_location=StorageLocation(name="Freezer A", location=parent)
        )
        ```
        """
        matching = self.get_all(
            name=storage_location.name, location=storage_location.location, exact_match=True
        )
        for m in matching:
            if m.name.lower() == storage_location.name.lower():
                logging.warning(
                    f"Storage location with name {storage_location.name} already exists, returning existing."
                )
                return m
        return self.create(storage_location=storage_location)

    def delete(self, *, id: str) -> None:
        """Delete a Storage Location by its Albert ID.

        Parameters
        ----------
        id : str
            The Albert ID of the storage location to delete.

        Returns
        -------
        None

        Examples
        --------
        ```python
        client.storage_locations.delete(id="STL1")
        ```
        """
        path = f"{self.base_path}/{id}"
        self.session.delete(path)

    def update(self, *, storage_location: StorageLocation) -> StorageLocation:
        """Update an existing Storage Location.

        Fetch a storage location (e.g. via [`get_by_id`][albert.collections.storage_locations.StorageLocationsCollection.get_by_id]),
        modify its name, then pass it here. The storage location is matched by its ``id``.

        Parameters
        ----------
        storage_location : StorageLocation
            The storage location to update. Its ``id`` must be set.

        Returns
        -------
        StorageLocation
            The updated storage location, re-fetched from Albert.

        Notes
        -----
        Only the ``name`` field can be updated.

        Examples
        --------
        ```python
        storage_location = client.storage_locations.get_by_id(id="STL1")
        storage_location.name = "Freezer A (relocated)"
        updated = client.storage_locations.update(storage_location=storage_location)
        ```
        """
        path = f"{self.base_path}/{storage_location.id}"
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=storage_location.id),
            updated=storage_location,
        )
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=storage_location.id)
