from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import BTDatasetId
from albert.resources.btdataset import BTDataset


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
        name: str | None = None,
        created_by: str | None = None,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[BTDataset]:
        """
        Get all items from the BTDataset collection.

        Parameters
        ----------
        name : str, optional
            Filter datasets by name.
        created_by : str, optional
            Filter datasets by the user who created them.
        start_key : str, optional
            Start key for paginated results.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.

        Returns
        -------
        Iterator[BTDataset]
            An iterator over BTDataset items.
        """
        params = {
            "startKey": start_key,
            "createdBy": created_by,
            "name": name,
        }
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [BTDataset(**item) for item in items],
        )
