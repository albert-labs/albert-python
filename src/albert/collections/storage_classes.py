from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.resources.storage_classes import StorageClass


class StorageClassesCollection(BaseCollection):
    """Collection for interacting with storage class compatibility endpoints."""

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{self._api_version}/static/storageclass"

    @validate_call
    def get_all(self) -> list[StorageClass]:
        """Retrieve storage compatibility information for all storage classes."""
        response = self.session.get(self.base_path)
        return [StorageClass(**item) for item in response.json()]
