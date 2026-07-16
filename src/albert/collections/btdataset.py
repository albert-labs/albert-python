from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import BTDatasetId
from albert.resources.btdataset import BTDataset


class BTDatasetCollection(BaseCollection):
    """Manage Breakthrough datasets in the Albert platform.

    Albert Breakthrough is Albert's inverse-design / ML optimization capability. A **dataset**
    ([`BTDataset`][albert.resources.btdataset.BTDataset]) is the tabular data used to
    build and train Breakthrough models. A dataset can reference the Albert entities
    it was assembled from (projects, data columns, targets, and worksheets) via its
    ``references``. Datasets feed into model sessions and models
    ([`BTModelSessionCollection`][albert.collections.btmodel.BTModelSessionCollection],
    [`BTModelCollection`][albert.collections.btmodel.BTModelCollection]), whose ``dataset_id``
    points back here.

    Datasets are identified by a dataset ID (format ``DST...``, e.g. ``"DST1"``).

    This collection is accessed as ``client.btdatasets``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for dataset requests.

    Methods
    -------
    create(dataset) -> BTDataset
        Create a new dataset.
    get_by_id(id) -> BTDataset
        Get a single dataset by its ID.
    get_all(...) -> Iterator[BTDataset]
        Iterate over datasets, optionally filtered by name or creator.
    update(dataset) -> BTDataset
        Update an existing dataset.
    delete(id) -> None
        Delete a dataset by its ID.

    Examples
    --------
    ```python
    from albert import Albert

    client = Albert()
    dataset = client.btdatasets.get_by_id(id="DST1")
    dataset.name
    # 'Coatings training set'
    ```
    """

    _api_version = "v3"
    _updatable_attributes = {"name", "key", "file_name", "references"}

    def __init__(self, *, session: AlbertSession):
        """Initialize a BTDatasetCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{BTDatasetCollection._api_version}/btdataset"

    @validate_call
    def create(self, *, dataset: BTDataset) -> BTDataset:
        """Create a new dataset.

        Parameters
        ----------
        dataset : BTDataset
            The dataset to create. ``name`` is required. Set ``references`` to
            record which Albert entities the dataset was assembled from.

        Returns
        -------
        BTDataset
            The newly created dataset, populated with its assigned ID.

        Examples
        --------
        ```python
        from albert import Albert
        from albert.resources.btdataset import BTDataset

        client = Albert()
        dataset = BTDataset(name="Coatings training set")
        created = client.btdatasets.create(dataset=dataset)
        created.id
        # 'DST1'
        ```
        """
        response = self.session.post(
            self.base_path,
            json=dataset.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return BTDataset(**response.json())

    @validate_call
    def get_by_id(self, *, id: BTDatasetId) -> BTDataset:
        """Get a single dataset by its ID.

        Parameters
        ----------
        id : BTDatasetId
            The dataset ID (format ``DST...``, e.g. ``"DST1"``).

        Returns
        -------
        BTDataset
            The fully populated dataset.

        Examples
        --------
        ```python
        dataset = client.btdatasets.get_by_id(id="DST1")
        dataset.name
        # 'Coatings training set'
        ```
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return BTDataset(**response.json())

    @validate_call
    def update(self, *, dataset: BTDataset) -> BTDataset:
        """Update an existing dataset.

        Fetch the dataset (e.g. with [`get_by_id`][albert.collections.btdataset.BTDatasetCollection.get_by_id]), modify the updatable
        fields on the returned object, then pass it here. Only the fields listed in
        Notes are applied; changes to other fields are ignored.

        Parameters
        ----------
        dataset : BTDataset
            The dataset to update. Must have a valid ``id``.

        Returns
        -------
        BTDataset
            The updated dataset.

        Notes
        -----
        The following fields can be updated: ``file_name``, ``key``, ``name``,
        ``references``.

        Examples
        --------
        ```python
        dataset = client.btdatasets.get_by_id(id="DST1")
        dataset.name = "Coatings training set (v2)"
        updated = client.btdatasets.update(dataset=dataset)
        updated.name
        # 'Coatings training set (v2)'
        ```
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
        """Delete a dataset by its ID.

        Parameters
        ----------
        id : BTDatasetId
            The dataset ID to delete (format ``DST...``).

        Returns
        -------
        None

        Examples
        --------
        ```python
        client.btdatasets.delete(id="DST1")
        ```
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
        """Iterate over datasets, optionally filtered by name or creator.

        Results are returned as a lazily paginated iterator, so iterating fetches
        additional pages on demand.

        Parameters
        ----------
        name : str, optional
            Filter datasets by name.
        created_by : str, optional
            Filter datasets by the user who created them.
        start_key : str, optional
            Resume pagination from this key (from a previous partial iteration).
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Returns
        -------
        Iterator[BTDataset]
            A lazily paginated iterator over datasets.

        Examples
        --------
        ```python
        for dataset in client.btdatasets.get_all(max_items=25):
            print(dataset.id, dataset.name)
        ```
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
