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
    """A collection for managing smart datasets in the Albert platform (🧪Beta).

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    Parameters
    ----------
    session : AlbertSession
        The Albert session instance.

    Attributes
    ----------
    base_path : str
        The base URL for smart dataset API requests.

    Methods
    -------
    create(scope, build=True) -> SmartDataset
        Creates a new smart dataset entity.
    get_all(max_items=None) -> Iterator[SmartDataset]
        Lists all smart datasets for the tenant.
    get_by_id(id) -> SmartDataset
        Retrieves a smart dataset by its ID.
    update(smart_dataset, build=True) -> SmartDataset
        Updates a smart dataset.
    delete(id) -> None
        Deletes a smart dataset by its ID.
    get_data(id, aggregate_by=None, ids=None, variables=None) -> SmartDatasetData
        Retrieves the data for a smart dataset.
    """

    _api_version = "v3"

    _updatable_attributes = {"scope", "build_state", "storage_key", "schema_"}

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the SmartDatasetCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
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
        """
        Creates a new smart dataset entity.

        Parameters
        ----------
        scope : SmartDatasetScope
            The scope of the smart dataset.
        parent_id : ProjectId, optional
            The ID of the parent project to inherit the ACL policy from. When set,
            the smart dataset inherits its ACL policy from the referenced project.
        build : bool, optional
            Whether to populate the smart dataset with data from Albert.

        Returns
        -------
        SmartDataset
            The created smart dataset entity.
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

    def get_all(
        self,
        *,
        max_items: int | None = None,
    ) -> Iterator[SmartDataset]:
        """
        List all smart datasets for the tenant.

        Parameters
        ----------
        max_items : int, optional
            Maximum number of items to return. If None, returns all available items.

        Returns
        -------
        Iterator[SmartDataset]
            An iterator of SmartDataset entities.
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
        """
        Retrieves a smart dataset by its ID.

        Parameters
        ----------
        id : SmartDatasetId
            The ID of the smart dataset to retrieve.
        parent_id : ProjectId, optional
            The ID of the parent project to inherit the ACL policy from when
            the caller does not own the smart dataset record.

        Returns
        -------
        SmartDataset
            The SmartDataset entity.
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
        """
        Update a smart dataset.

        Parameters
        ----------
        smart_dataset : SmartDataset
            The smart dataset with updated fields. Must have an id set.

        Returns
        -------
        SmartDataset
            The updated SmartDataset.
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
        """
        Deletes a smart dataset by its ID.

        Parameters
        ----------
        id : SmartDatasetId
            The ID of the smart dataset to delete.

        Returns
        -------
        None
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
        """
        Retrieves the experiment data for a smart dataset.

        Parameters
        ----------
        id : SmartDatasetId
            The ID of the smart dataset.
        parent_id : ProjectId, optional
            The ID of the parent project to inherit the ACL policy from when
            the caller does not own the smart dataset record.
        aggregate_by : SmartDatasetAggregateBy, optional
            The aggregation level for the returned data. Defaults to ``ptd``.
        ids : list[str], optional
            Filter results to these identifier keys.
        variables : list[str], optional
            Filter results to these variable keys.

        Returns
        -------
        SmartDatasetData
            The experiment data matrix.
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
