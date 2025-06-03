import json
import logging
from collections.abc import Generator, Iterator

from albert.collections.base import BaseCollection
from albert.exceptions import AlbertHTTPError
from albert.resources.base import EntityLink
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocation
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode


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

    def list(
        self,
        *,
        name: str | list[str] | None = None,
        exact_match: bool = False,
        location: str | Location | None = None,
        start_key: str | None = None,
        limit: int = 50,
    ) -> Generator[StorageLocation, None, None]:
        """List storage locations with optional filtering.

        Parameters
        ----------
        name : str | list[str] | None, optional
            The name or names of the storage locations to filter by, by default None
        exact_match : bool, optional
            Whether to perform an exact match on the name, by default False
        location : str | Location | None, optional
            The location ID or Location object to filter by, by default None

        Yields
        ------
        Generator[StorageLocation, None, None]
            _description_
        """

        def deserialize(items: list[dict]) -> Iterator[StorageLocation]:
            for x in items:
                id = x["albertId"]
                try:
                    yield self.get_by_id(id=id)
                except AlbertHTTPError as e:
                    logger.warning(f"Error fetching storage location {id}: {e}")

        params = {
            "limit": limit,
            "locationId": location.id if isinstance(location, Location | EntityLink) else location,
            "startKey": start_key,
        }
        if name:
            params["name"] = [name] if isinstance(name, str) else name
            params["exactMatch"] = json.dumps(exact_match)

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
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
        matching = self.list(
            name=storage_location.name, location=storage_location.location, exact_match=True
        )
        for m in matching:
            if m.name.lower() == storage_location.name.lower():
                logging.warning(
                    f"Storage location with name {storage_location.name} already exists, returning existing."
                )
                return m

        path = self.base_path
        response = self.session.post(
            path, json=storage_location.model_dump(by_alias=True, exclude_none=True, mode="json")
        )
        return StorageLocation(**response.json())

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
