from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import PaginationMode
from albert.core.shared.identifiers import ProjectId, SmartDatasetId
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.resources.smart_datasets import (
    SmartDataset,
    SmartDatasetAggregateBy,
    SmartDatasetBuildState,
    SmartDatasetData,
    SmartDatasetScope,
)


class SmartDatasetCollection(BaseCollection):
    """Manage Smart Datasets in the Albert platform (🧪Beta).

    A Smart Dataset assembles experiment data from a defined scope (projects,
    targets, and worksheets) into a single record-by-variable matrix ready for
    analysis and modeling. Records are the experiments (or materials,
    lots, or measurements, depending on the aggregation level), and variables are
    the material amounts, parameters, molecules, and measured properties observed
    across those experiments.

    A Smart Dataset is built asynchronously: after [`create`][albert.collections.smart_datasets.SmartDatasetCollection.create] (or an
    [`update`][albert.collections.smart_datasets.SmartDatasetCollection.update] that changes the scope) the dataset moves through a build state
    ([`SmartDatasetBuildState`][albert.resources.smart_datasets.SmartDatasetBuildState]) and only
    exposes its data once it is ``ready``. Use [`get_data`][albert.collections.smart_datasets.SmartDatasetCollection.get_data] to pull the built
    matrix, choosing how rows are aggregated with
    [`SmartDatasetAggregateBy`][albert.resources.smart_datasets.SmartDatasetAggregateBy].

    Smart Datasets are referenced by their Smart Dataset ID (format ``SDT...``).
    They aggregate the same experiment Property Data managed through
    [`PropertyDataCollection`][albert.collections.property_data.PropertyDataCollection].

    A [`SmartDataset`][albert.resources.smart_datasets.SmartDataset] and a
    [`BTDataset`][albert.resources.btdataset.BTDataset] are distinct entities that share
    an ETL engine (Zeus stored procedures) but are not interchangeable: a
    ``BTDataset`` is a Breakthrough pointer record (its dataset rows are stored in
    S3), while a ``SmartDataset`` is a Smart Projects entity (also S3-backed, via
    ``storage_key`` and ``schema_``). A SmartDataset is not itself an input to
    Albert Breakthrough.

    This collection is accessed as ``client.smart_datasets``.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for smart dataset requests.

    Methods
    -------
    create(scope, parent_id=None, build=True) -> SmartDataset
        Create a new smart dataset from a scope and (optionally) build it.
    get_all(max_items=None) -> Iterator[SmartDataset]
        Iterate over all smart datasets for the tenant.
    get_by_id(id, parent_id=None) -> SmartDataset
        Retrieve a single smart dataset by its Smart Dataset ID.
    update(smart_dataset) -> SmartDataset
        Apply changes to an existing smart dataset.
    delete(id) -> None
        Delete a smart dataset by its Smart Dataset ID.
    get_data(id, parent_id=None, aggregate_by=..., ids=None, variables=None) -> SmartDatasetData
        Retrieve the built experiment data matrix for a smart dataset.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.smart_datasets import SmartDatasetScope

        client = Albert()
        # Build a smart dataset scoped to a single project
        ds = client.smart_datasets.create(
            scope=SmartDatasetScope(project_ids=["PRO123"]),
        )
        # Once ready, pull the experiment data matrix
        data = client.smart_datasets.get_data(id=ds.id)
        print(data.data)
        ```
    """

    _api_version = "v3"

    _updatable_attributes = {"scope", "build_state", "storage_key", "schema_"}

    def __init__(self, *, session: AlbertSession):
        """Initialize a SmartDatasetCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{SmartDatasetCollection._api_version}/smartdatasets"

    @validate_call
    def create(
        self,
        *,
        scope: SmartDatasetScope,
        parent_id: ProjectId | None = None,
        build: bool = True,
    ) -> SmartDataset:
        """Create a new smart dataset.

        The ``scope`` defines which experiments feed the dataset (by project,
        target, and optionally worksheet). When ``build`` is True the dataset is
        populated asynchronously from Albert; poll its
        [`build_state`][albert.resources.smart_datasets.SmartDataset.build_state] (or
        re-fetch with [`get_by_id`][albert.collections.smart_datasets.SmartDatasetCollection.get_by_id]) until it reaches ``ready`` before calling
        [`get_data`][albert.collections.smart_datasets.SmartDatasetCollection.get_data].

        Parameters
        ----------
        scope : SmartDatasetScope
            The scope defining which projects, targets, and worksheets the dataset
            draws its experiment data from.
        parent_id : ProjectId, optional
            The ID of the parent project to inherit the ACL policy from. When set,
            the smart dataset inherits its ACL policy from the referenced project.
        build : bool, optional
            Whether to populate the smart dataset with data from Albert. Defaults
            to True.

        Returns
        -------
        SmartDataset
            The created smart dataset, populated with its assigned Smart Dataset ID.

        !!! example
            ```python
            from albert import Albert
            from albert.resources.smart_datasets import SmartDatasetScope

            client = Albert()
            ds = client.smart_datasets.create(
                scope=SmartDatasetScope(project_ids=["PRO123"]),
            )
            print(ds.id, ds.build_state)
            ```
        """
        body = {"scope": scope.model_dump(by_alias=True, exclude_none=False, mode="json")}
        if parent_id is not None:
            body["parentId"] = parent_id
        response = self.session.post(
            self.base_path,
            json=body,
            params={"build": build},
        )
        return SmartDataset(**response.json())

    @validate_call
    def get_all(
        self,
        *,
        max_items: int | None = None,
    ) -> Iterator[SmartDataset]:
        """Iterate over all smart datasets for the tenant.

        Parameters
        ----------
        max_items : int, optional
            Maximum number of datasets to return. If None, returns all available
            datasets, fetching additional pages as the iterator is consumed.

        Returns
        -------
        Iterator[SmartDataset]
            An iterator over the tenant's smart datasets.

        !!! example
            ```python
            for ds in client.smart_datasets.get_all(max_items=10):
                print(ds.id, ds.build_state)
            ```
        """
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            max_items=max_items,
            deserialize=lambda items: [SmartDataset(**item) for item in items],
        )

    @validate_call
    def get_by_id(self, *, id: SmartDatasetId, parent_id: ProjectId | None = None) -> SmartDataset:
        """Retrieve a single smart dataset by its Smart Dataset ID.

        Parameters
        ----------
        id : SmartDatasetId
            The Smart Dataset ID (format ``SDT...``) of the dataset to retrieve.
        parent_id : ProjectId, optional
            The ID of the parent project to inherit the ACL policy from when
            the caller does not own the smart dataset record.

        Returns
        -------
        SmartDataset
            The requested smart dataset.

        !!! example
            ```python
            ds = client.smart_datasets.get_by_id(id="SDT123")
            print(ds.build_state)
            ```
        """
        url = f"{self.base_path}/{id}"
        params = {"parentId": parent_id} if parent_id is not None else None
        response = self.session.get(url, params=params)
        return SmartDataset(**response.json())

    @validate_call
    def update(
        self,
        *,
        smart_dataset: SmartDataset,
    ) -> SmartDataset:
        """Apply changes to an existing smart dataset.

        The current server-side record is fetched and diffed against the supplied
        ``smart_dataset``; only changed, updatable fields are patched. Pass an
        object retrieved via [`get_by_id`][albert.collections.smart_datasets.SmartDatasetCollection.get_by_id] with the desired fields modified.

        Parameters
        ----------
        smart_dataset : SmartDataset
            The smart dataset with updated fields. Its ``id`` must be set.

        Returns
        -------
        SmartDataset
            The updated smart dataset, re-fetched after the patch is applied.

        Notes
        -----
        Only the following fields are updatable: ``scope``, ``build_state``,
        ``storage_key``, and ``schema_``. Changes to any other field are ignored.

        !!! example
            ```python
            from albert.resources.smart_datasets import SmartDatasetScope

            ds = client.smart_datasets.get_by_id(id="SDT123")
            ds.scope = SmartDatasetScope(project_ids=["PRO123", "PRO456"])
            updated = client.smart_datasets.update(smart_dataset=ds)
            ```
        """
        existing = self.get_by_id(id=smart_dataset.id, parent_id=smart_dataset.parent_id)
        payload = self._generate_patch_payload(existing=existing, updated=smart_dataset)
        if payload.data:
            self.session.patch(
                url=f"{self.base_path}/{smart_dataset.id}",
                json=payload.model_dump(mode="json", by_alias=True, exclude_none=False),
            )
        return self.get_by_id(id=smart_dataset.id, parent_id=smart_dataset.parent_id)

    def _generate_patch_payload(
        self,
        *,
        existing: SmartDataset,
        updated: SmartDataset,
    ) -> PatchPayload:
        data = []
        for attribute in self._updatable_attributes:
            if attribute not in updated.model_fields_set:
                continue
            old_value = getattr(existing, attribute, None)
            new_value = getattr(updated, attribute, None)

            # Get the serialization alias name for the attribute, if it exists
            field_info = existing.__class__.model_fields[attribute]
            alias = (
                getattr(field_info, "serialization_alias", None) or field_info.alias or attribute
            )

            if new_value != old_value:
                # Update existing attribute
                data.append(
                    PatchDatum(
                        attribute=alias,
                        operation=PatchOperation.UPDATE,
                        old_value=old_value,
                        new_value=new_value,
                    )
                )

        return PatchPayload(data=data)

    @validate_call
    def delete(self, *, id: SmartDatasetId) -> None:
        """Delete a smart dataset by its Smart Dataset ID.

        Parameters
        ----------
        id : SmartDatasetId
            The Smart Dataset ID (format ``SDT...``) of the dataset to delete.

        Returns
        -------
        None

        !!! example
            ```python
            client.smart_datasets.delete(id="SDT123")
            ```
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)

    @validate_call
    def get_data(
        self,
        *,
        id: SmartDatasetId,
        parent_id: ProjectId | None = None,
        aggregate_by: SmartDatasetAggregateBy = SmartDatasetAggregateBy.PTD,
        ids: list[str] | None = None,
        variables: list[str] | None = None,
    ) -> SmartDatasetData:
        """Retrieve the built experiment data matrix for a smart dataset.

        Returns the record-by-variable matrix assembled by the dataset, along with
        the identifier metadata for each row and the variable metadata for each
        column. The dataset must be built and ``ready`` before its data can be
        retrieved.

        Parameters
        ----------
        id : SmartDatasetId
            The Smart Dataset ID (format ``SDT...``) of the dataset.
        parent_id : ProjectId, optional
            The ID of the parent project to inherit the ACL policy from when
            the caller does not own the smart dataset record.
        aggregate_by : SmartDatasetAggregateBy, optional
            The aggregation level for the returned records (rows). Defaults to
            ``SmartDatasetAggregateBy.PTD`` (per measurement / property data point).
        ids : list[str], optional
            Restrict the returned rows to these record identifier keys.
        variables : list[str], optional
            Restrict the returned columns to these variable keys.

        Returns
        -------
        SmartDatasetData
            The experiment data matrix with its identifiers and variable metadata.

        Raises
        ------
        ValueError
            If the smart dataset's build state is not ``ready``.

        !!! example
            ```python
            from albert.resources.smart_datasets import SmartDatasetAggregateBy

            data = client.smart_datasets.get_data(
                id="SDT123",
                aggregate_by=SmartDatasetAggregateBy.WFL,
            )
            print(data.data)
            ```
        """
        smart_dataset = self.get_by_id(id=id, parent_id=parent_id)
        if smart_dataset.build_state != SmartDatasetBuildState.READY:
            raise ValueError("Smart dataset is not ready")
        params: dict = {"aggregate_by": aggregate_by.to_api_value()}
        if ids is not None:
            params["id"] = ids
        if variables is not None:
            params["variable"] = variables
        response = self.session.get(
            f"{self.base_path}/{id}/experiments/data",
            params=params,
        )
        data = response.json()
        data["aggregate_by"] = aggregate_by.from_api_value(data["aggregate_by"])
        return SmartDatasetData(**data)
