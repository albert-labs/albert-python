from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.resources.storage_classes import StorageClass


class StorageClassesCollection(BaseCollection):
    """Access hazardous-materials Storage Classes in the Albert platform.

    A Storage Class is a hazardous-materials storage classification that governs
    which materials may be safely stored together. Each class carries a
    compatibility matrix listing the
    other classes it may, may not, or may with warnings be co-stored with.
    Inventory Items carry a storage/security class that ties back to these
    classifications.

    Storage classes are reference data served from a static endpoint, so this
    collection is read-only.

    This collection is accessed as ``client.storage_classes``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for storage class requests.

    Methods
    -------
    get_all() -> list[StorageClass]
        Retrieve every storage class and its compatibility matrix.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert
        client = Albert()
        for storage_class in client.storage_classes.get_all():
            print(storage_class.storage_class_number, storage_class.storage_class_name)
        ```
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{self._api_version}/static/storageclass"

    @validate_call
    def get_all(self) -> list[StorageClass]:
        """Retrieve every Storage Class and its compatibility matrix.

        Returns
        -------
        list[StorageClass]
            All storage class records, each with its co-storage compatibility
            matrix.

        Examples
        --------
        !!! example
            ```python
            storage_classes = client.storage_classes.get_all()
            for storage_class in storage_classes:
                print(storage_class.storage_class_name)
            ```
        """
        response = self.session.get(self.base_path)
        return [StorageClass(**item) for item in response.json()]
