import logging
from collections.abc import Iterator

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.models.base import EntityLink
from albert.exceptions import AlbertHTTPError
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocation


class StorageLocationsCollection(BaseCollection):
    """StorageLocationsCollection is a collection class for managing StorageLoction entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {"name"}

    def __init__(self, *, session: AlbertSession):
        """Initialize the StorageLocationsCollection.

        Parameters
        ----------
        session : AlbertSession
            The Albert Session information
        """
        super().__init__(session=session)
        self.base_path = f"/api/{StorageLocationsCollection._api_version}/storagelocations"

    def get_by_id(self, *, id: str) -> StorageLocation:
        """Get a storage location by its ID.

        Parameters
        ----------
        id : str
            The ID of the storage location to retrieve.

        Returns
        -------
        StorageLocation
            The retrieved storage location with the given ID.
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
        """
        Get all storage locations with optional filtering.

        Parameters
        ----------
        name : str or list[str], optional
            The name or names of the storage locations to filter by.
        exact_match : bool, optional
            Whether to perform an exact match on the name(s). Default is False.
        location : str or Location, optional
            A location ID or Location object to filter by.
        start_key : str, optional
            The pagination key to start from.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[StorageLocation]
            An iterator over StorageLocation items matching the search criteria.
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

        if name:
            params["name"] = [name] if isinstance(name, str) else name
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
        """Create a new storage location.

        Parameters
        ----------
        storage_location : StorageLocation
            The storage location to create.

        Returns
        -------
        StorageLocation
            The created storage location.
        """
        response = self.session.post(
            self.base_path,
            json=storage_location.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return StorageLocation(**response.json())

    def get_or_create(self, *, storage_location: StorageLocation) -> StorageLocation:
        """Get or create a storage location.

        Parameters
        ----------
        storage_location : StorageLocation
            The storage location to get or create.

        Returns
        -------
        StorageLocation
            The existing or newly created storage location.
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
        """Delete a storage location by its ID.

        Parameters
        ----------
        id : str
            The ID of the storage location to delete.
        """
        path = f"{self.base_path}/{id}"
        self.session.delete(path)

    def update(self, *, storage_location: StorageLocation) -> StorageLocation:
        """Update a storage location.

        Parameters
        ----------
        storage_location : StorageLocation
            The storage location to update.

        Returns
        -------
        StorageLocation
            The updated storage location as returned by the server.
        """
        path = f"{self.base_path}/{storage_location.id}"
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=storage_location.id),
            updated=storage_location,
        )
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=storage_location.id)
