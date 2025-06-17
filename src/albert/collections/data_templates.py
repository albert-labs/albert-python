from collections.abc import Iterator
from itertools import islice

from pydantic import Field

from albert.collections.base import BaseCollection
from albert.exceptions import AlbertHTTPError
from albert.resources.base import OrderBy
from albert.resources.data_templates import DataColumnValue, DataTemplate, DataTemplateSearchItem
from albert.resources.identifiers import DataTemplateId
from albert.resources.parameter_groups import PGPatchPayload
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode
from albert.utils.patch_types import GeneralPatchDatum
from albert.utils.patches import (
    _split_patch_types_for_params_and_data_cols,
)


class DCPatchDatum(PGPatchPayload):
    data: list[GeneralPatchDatum] = Field(
        default_factory=list,
        description="The data to be updated in the data column.",
    )


class DataTemplateCollection(BaseCollection):
    """DataTemplateCollection is a collection class for managing DataTemplate entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {"name", "description", "metadata"}

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{DataTemplateCollection._api_version}/datatemplates"

    def create(self, *, data_template: DataTemplate) -> DataTemplate:
        """Creates a new data template.

        Parameters
        ----------
        data_template : DataTemplate
            The DataTemplate object to create.

        Returns
        -------
        DataTemplate
            The registered DataTemplate object with an ID.
        """
        # Preprocess data_column_values to set validation to None if it is an empty list
        # Handle a bug in the API where validation is an empty list
        # https://support.albertinvent.com/hc/en-us/requests/9177
        for column_value in data_template.data_column_values:
            if isinstance(column_value.validation, list) and len(column_value.validation) == 0:
                column_value.validation = None

        response = self.session.post(
            self.base_path,
            json=data_template.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return DataTemplate(**response.json())

    def get_by_id(self, *, id: DataTemplateId) -> DataTemplate:
        """Get a data template by its ID.

        Parameters
        ----------
        id : DataTemplateId
            The ID of the data template to get.

        Returns
        -------
        DataTemplate
            The data template object on match or None
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return DataTemplate(**response.json())

    def get_by_ids(self, *, ids: list[DataTemplateId]) -> list[DataTemplate]:
        """Get a list of data templates by their IDs.

        Parameters
        ----------
        ids : list[DataTemplateId]
            The list of DataTemplate IDs to get.

        Returns
        -------
        list[DataTemplate]
            A list of DataTemplate objects with the provided IDs.
        """
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 250] for i in range(0, len(ids), 250)]
        return [
            DataTemplate(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()["Items"]
        ]

    def get_by_name(self, *, name: str) -> DataTemplate | None:
        """Get a data template by its name.

        Parameters
        ----------
        name : str
            The name of the data template to get.

        Returns
        -------
        DataTemplate | None
            The matching data template object or None if not found.
        """
        hits = list(self.get_all(name=name))
        for h in hits:
            if h.name.lower() == name.lower():
                return h
        return None

    def add_data_columns(
        self, *, data_template_id: str, data_columns: list[DataColumnValue]
    ) -> DataTemplate:
        """Adds data columns to a data template.

        Parameters
        ----------
        data_template_id : str
            The ID of the data template to add the columns to.
        data_columns : list[DataColumnValue]
            The list of DataColumnValue objects to add to the data template.

        Returns
        -------
        DataTemplate
            The updated DataTemplate object.
        """
        payload = {
            "DataColumns": [
                x.model_dump(mode="json", by_alias=True, exclude_none=True) for x in data_columns
            ]
        }
        self.session.put(
            f"{self.base_path}/{data_template_id}/datacolumns",
            json=payload,
        )
        return self.get_by_id(id=data_template_id)

    def search(
        self,
        *,
        name: str | None = None,
        user_id: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        limit: int = 100,
        offset: int = 0,
    ) -> Iterator[DataTemplateSearchItem]:
        """Search for DataTemplate matching the provided criteria.

        ⚠️ This method returns partial (unhydrated) entities to optimize performance.
        To retrieve fully detailed entities, use :meth:`get_all` instead.

        Parameters
        ----------
        name : Union[str, None], optional
            The name of the data template to filter by, by default None.
        user_id : str, optional
            user_id to filter by, by default None.
        order_by : OrderBy, optional
            The order by which to sort the results, by default OrderBy.DESCENDING.

        Returns
        -------
        Iterator[DataTemplateSearchItem]
            An iterator of DataTemplateSearchItem objects matching the provided criteria.
        """

        params = {
            "limit": limit,
            "offset": offset,
            "order": OrderBy(order_by).value if order_by else None,
            "text": name,
            "userId": user_id,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            deserialize=lambda items: [DataTemplateSearchItem.model_validate(x) for x in items],
            params=params,
        )

    def update(self, *, data_template: DataTemplate) -> DataTemplate:
        """Updates a data template.

        Parameters
        ----------
        data_template : DataTemplate
            The DataTemplate object to update. The ID must be set and matching the ID of the DataTemplate to update.

        Returns
        -------
        DataTemplate
            The Updated DataTemplate object.
        """

        existing = self.get_by_id(id=data_template.id)
        base_payload = self._generate_patch_payload(existing=existing, updated=data_template)

        path = f"{self.base_path}/{existing.id}"
        # Handle special updates mainly for complex validations
        special_patches, special_enum_patches, new_param_patches = (
            _split_patch_types_for_params_and_data_cols(existing=existing, updated=data_template)
        )
        payload = DCPatchDatum(data=base_payload.data)

        payload.data.extend(special_patches)

        # handle adding new data columns
        if len(new_param_patches) > 0:
            self.session.put(
                f"{self.base_path}/{existing.id}/datacolumns",
                json={"DataColumns": new_param_patches},
            )
        # Handle special enum update data columns
        for sequence, enum_patches in special_enum_patches.items():
            if len(enum_patches) == 0:
                continue

            enum_path = f"{self.base_path}/{existing.id}/datacolumns/{sequence}/enums"
            self.session.put(enum_path, json=enum_patches)

        if len(payload.data) > 0:
            self.session.patch(
                path, json=payload.model_dump(mode="json", by_alias=True, exclude_none=True)
            )
        return self.get_by_id(id=data_template.id)

    def delete(self, *, id: str) -> None:
        """Deletes a data template by its ID.

        Parameters
        ----------
        id : str
            The ID of the data template to delete.
        """
        self.session.delete(f"{self.base_path}/{id}")

    def get_all(
        self,
        *,
        name: str | None = None,
        user_id: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        limit: int = 100,
        offset: int = 0,
    ) -> Iterator[DataTemplate]:
        """Retrieve fully hydrated DataTemplate entities with optional filters.

        This method returns complete entity data using `get_by_ids`.
        Use :meth:`search` for faster retrieval when you only need lightweight, partial (unhydrated) entities.
        """

        def batched(iterable, size):
            """Yield lists of up to `size` IDs from an iterable of objects with an `id` attribute."""

            it = (item.id for item in iterable)
            while batch := list(islice(it, size)):
                yield batch

        id_batches = batched(
            self.search(name=name, user_id=user_id, order_by=order_by, limit=limit, offset=offset),
            limit,  # batch size
        )

        for batch in id_batches:
            try:
                hydrated_templates = self.get_by_ids(ids=batch)
                yield from hydrated_templates
            except AlbertHTTPError as e:
                logger.warning(f"Error hydrating batch {batch}: {e}")
