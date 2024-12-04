import json
import logging
from collections.abc import Generator, Iterator

from albert.collections.base import BaseCollection
from albert.exceptions import AlbertHTTPError
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocation
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode


class StorageLocationsCollection(BaseCollection):
    _api_version = "v3"
    _updatable_attributes = {"name"}

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{StorageLocationsCollection._api_version}/storagelocations"

    def get_by_id(self, *, id: str) -> StorageLocation:
        path = f"{self.base_path}/{id}"
        response = self.session.get(path)
        return StorageLocation(**response.json())

    def list(
        self,
        *,
        limit: int = 50,
        name: str | list[str] | None = None,
        exact_match: bool = False,
        location: str | Location | None = None,
        start_key: str | None = None,
    ) -> Generator[StorageLocation, None, None]:
        def deserialize(items: list[dict]) -> Iterator[StorageLocation]:
            for x in items:
                id = x["albertId"]
                try:
                    yield self.get_by_id(id=id)
                except AlbertHTTPError as e:
                    logger.warning(f"Error fetching storage location {id}: {e}")

        params = {
            "limit": limit,
            "locationId": location.id if isinstance(location, Location) else location,
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
        matching = self.list(name=storage_location.name, exact_match=True)
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
        path = f"{self.base_path}/{id}"
        self.session.delete(path)

    def update(self, *, storage_location: StorageLocation) -> StorageLocation:
        path = f"{self.base_path}/{storage_location.id}"
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=storage_location.id),
            updated=storage_location,
        )
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=storage_location.id)
