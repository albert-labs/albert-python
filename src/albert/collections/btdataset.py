from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.resources.btdataset import BTDataset
from albert.resources.identifiers import BTDatasetId
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class BTDatasetCollection(BaseCollection):
    """
    BTDatasetCollection is a collection class for managing Breakthrough dataset entities.

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base path for btdataset API requests.
    """

    _api_version = "v3"
    _updatable_attributes = {"name", "key", "file_name", "references"}

    def __init__(self, *, session: AlbertSession):
        """
        Initialize the BTDatasetCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{BTDatasetCollection._api_version}/btdataset"

    @validate_call
    def create(self, *, dataset: BTDataset) -> BTDataset:
        """
        Create a new BTDataset.

        Parameters
        ----------
        dataset : BTDataset
            The BTDataset record to create.

        Returns
        -------
        BTDataset
            The created BTDataset.
        """
        response = self.session.post(
            self.base_path,
            json=dataset.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return BTDataset(**response.json())

    @validate_call
    def get_by_id(self, *, id: BTDatasetId) -> BTDataset:
        """
        Get a BTDataset by ID.

        Parameters
        ----------
        id : BTDatasetId
            The Albert ID of the BTDataset.

        Returns
        -------
        BTDataset
            The retrived BTDataset.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return BTDataset(**response.json())

    @validate_call
    def update(self, *, dataset: BTDataset) -> BTDataset:
        """
        Update a BTDataset.

        The provided dataset must be registered with an Albert ID.

        Parameters
        ----------
        dataset : BTDataset
            The BTDataset with updated fields.

        Returns
        -------
        BTDataset
            The updated BTDataset object.
        """
        path = f"{self.base_path}/{dataset.id}"
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=dataset.id),
            updated=dataset,
        )
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=dataset.id)

    @validate_call
    def delete(self, *, id: BTDatasetId) -> None:
        """Delete a BTDataset by ID.

        Parameters
        ----------
        id : BTDatasetId
            The ID of the BTDataset to delete.

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")

    @validate_call
    def get_all(
        self,
        *,
        limit: int = 100,
        name: str | None = None,
        start_key: str | None = None,
        created_by: str | None = None,
    ) -> Iterator[BTDataset]:
        """Get all items from the BTDataset collection.

        Parameters
        ----------
        limit : int, optional
            Number of items to return per page, default 100
        name : str, optional
            Name of the dataset to filter by, default None
        start_key : str, optional
            The starting key for pagination, default None
        created_by : str, optional
            The user who created the dataset, default None

        Returns
        -------
        Iterator[BTDataset]
            An iterator of elements returned by the BTDataset listing.
        """
        params = {
            "limit": limit,
            "startKey": start_key,
            "createdBy": created_by,
            "name": name,
        }
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            deserialize=lambda items: [BTDataset(**item) for item in items],
        )
