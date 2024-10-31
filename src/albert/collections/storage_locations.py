import logging
from collections.abc import Generator

from albert.collections.base import BaseCollection
from albert.resources.locations import Location
from albert.resources.storage_locations import StorageLocation
from albert.session import AlbertSession


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

    def _list_generator(
        self,
        *,
        name: list[str] | str | None = None,
        exact_match: bool = False,
        location: str | None = None,
        start_key: str | None = None,
        limit: int = 50,
    ) -> Generator[StorageLocation, None, None]:
        params = {"limit": limit}
        if name:
            params["name"] = name if isinstance(name, list) else [name]
            if exact_match:
                params["exactMatch"] = str(exact_match).lower()
        if location:
            params["locationId"] = location
        if start_key:  # pragma: no cover
            params["startKey"] = start_key
        while True:
            response = self.session.get(self.base_path, params=params)
            sl_data = response.json().get("Items", [])
            if not sl_data or sl_data == []:
                break
            for sl in sl_data:
                yield self.get_by_id(id=sl["albertId"])
            start_key = response.json().get("lastKey")
            if not start_key:
                break
            params["startKey"] = start_key

    def list(
        self,
        *,
        name: list[str] | str | None = None,
        limit: int | None = None,
        exact_match: bool = False,
        location: str | Location | None = None,
    ) -> Generator[StorageLocation, None, None]:
        if location is not None:
            location = location.id if isinstance(location, Location) else location
        return self._list_generator(
            name=name,
            limit=limit,
            location=location,
            exact_match=exact_match,
        )

    def create(self, *, storage_location: StorageLocation) -> StorageLocation:
        matching = next(self.list(name=storage_location.name, exact_match=True), None)
        if matching is not None:
            logging.warning(
                f"Storage location with name {storage_location.name} already exists, returning existing."
            )
            return matching

        path = self.base_path
        response = self.session.post(
            path, json=storage_location.model_dump(by_alias=True, exclude_none=True)
        )
        return StorageLocation(**response.json())

    def delete(self, *, id: str) -> None:
        path = f"{self.base_path}/{id}"
        self.session.delete(path)

    def update(self, *, storage_location: StorageLocation) -> StorageLocation:
        path = f"{self.base_path}/{storage_location.id}"
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=storage_location.id), updated=storage_location
        )
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=storage_location.id)
