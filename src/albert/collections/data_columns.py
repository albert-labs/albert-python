import json
from collections.abc import Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.exceptions import AlbertHTTPError
from albert.resources.data_columns import DataColumn
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode


class DataColumnCollection(BaseCollection):
    """DataColumnCollection is a collection class for managing DataColumn entities in the Albert platform."""

    _api_version = "v3"
    _updatable_attributes = {"name", "metadata"}

    def __init__(self, *, session: AlbertSession):
        """Initialize the DataColumnCollection with the provided session."""
        super().__init__(session=session)
        self.base_path = f"/api/{DataColumnCollection._api_version}/datacolumns"

    def get_by_name(self, *, name) -> DataColumn | None:
        """
        Get a data column by its name.

        Parameters
        ----------
        name : str
            The name of the data column to get.

        Returns
        -------
        DataColumn | None
            The data column object on match or None
        """
        for dc in self.list(name=name):
            if dc.name.lower() == name.lower():
                return dc
        return None

    def get_by_id(self, *, id) -> DataColumn:
        """
        Get a data column by its ID.

        Parameters
        ----------
        id : str
            The ID of the data column to get.

        Returns
        -------
        DataColumn | None
            The data column object on match or None
        """
        response = self.session.get(f"{self.base_path}/{id}")
        dc = DataColumn(**response.json())
        return dc

    def list(
        self,
        *,
        order_by: OrderBy = OrderBy.DESCENDING,
        ids: str | list[str] | None = None,
        name: str | list[str] | None = None,
        exact_match: bool | None = None,
        default: bool | None = None,
        start_key: str | None = None,
        limit: int = 100,
        return_full: bool = True,
    ) -> Iterator[DataColumn]:
        """
        Lists data column entities with optional filters.

        Parameters
        ----------
        order_by : OrderBy, optional
            The order by which to sort the results, by default OrderBy.DESCENDING.
        ids: str | list[str] | None, optional
            Data column IDs to filter the search by, default None.
        name : Union[str, None], optional
            The name of the tag to filter by, by default None.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.
        default : bool, optional
            Whether to return only default columns, by default None.
        return_full : bool, optional
            Whether to make additional API call to fetch the full object, by default True

        Returns
        -------
        Iterator[DataColumn]
            An iterator of DataColumns matching the provided criteria.
        """

        def deserialize(items: list[dict]) -> Iterator[DataColumn]:
            if return_full:
                for item in items:
                    id = item["albertId"]
                    try:
                        yield self.get_by_id(id=id)
                    except AlbertHTTPError as e:
                        logger.warning(f"Error fetching Data Column '{id}': {e}")
            else:
                yield from (DataColumn(**item) for item in items)

        params = {
            "limit": limit,
            "orderBy": order_by.value,
            "startKey": start_key,
            "name": [name] if isinstance(name, str) else name,
            "exactMatch": json.dumps(exact_match) if exact_match is not None else None,
            "default": json.dumps(default) if default is not None else None,
            "dataColumns": [ids] if isinstance(ids, str) else ids,
        }
        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            deserialize=deserialize,
        )

    def create(self, *, data_column: DataColumn) -> DataColumn:
        """
        Create a new data column entity.

        Parameters
        ----------
        data_column : DataColumn
            The data column object to create.

        Returns
        -------
        DataColumn
            The created data column object.
        """
        payload = [data_column.model_dump(by_alias=True, exclude_unset=True, mode="json")]
        response = self.session.post(self.base_path, json=payload)

        return DataColumn(**response.json()[0])

    def delete(self, *, id: str) -> None:
        """
        Delete a data column entity.

        Parameters
        ----------
        id : str
            The ID of the data column object to delete.

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")

    def _is_metadata_item_list(
        self, *, existing_object: DataColumn, updated_object: DataColumn, metadata_field: str
    ):
        if not metadata_field.startswith("Metadata."):
            return False
        else:
            metadata_field = metadata_field.split(".")[1]
        if existing_object.metadata is None:
            existing_object.metadata = {}
        if updated_object.metadata is None:
            updated_object.metadata = {}
        existing = existing_object.metadata.get(metadata_field, None)
        updated = updated_object.metadata.get(metadata_field, None)
        return isinstance(existing, list) or isinstance(updated, list)

    def update(self, *, data_column: DataColumn) -> DataColumn:
        """Update a data column entity.

        Parameters
        ----------
        data_column : DataColumn
            The updated data column object. The ID must be set and match an existing data column.

        Returns
        -------
        DataColumn
            The updated data column object as registered in Albert.
        """
        existing = self.get_by_id(id=data_column.id)
        payload = self._generate_patch_payload(
            existing=existing,
            updated=data_column,
        )
        payload_dump = payload.model_dump(mode="json", by_alias=True)
        for i, change in enumerate(payload_dump["data"]):
            if not self._is_metadata_item_list(
                existing_object=existing,
                updated_object=data_column,
                metadata_field=change["attribute"],
            ):
                change["operation"] = "update"
                if "newValue" in change and change["newValue"] is None:
                    del change["newValue"]
                if "oldValue" in change and change["oldValue"] is None:
                    del change["oldValue"]
                payload_dump["data"][i] = change
        if len(payload_dump["data"]) == 0:
            return data_column
        for e in payload_dump["data"]:
            self.session.patch(
                f"{self.base_path}/{data_column.id}",
                json={"data": [e]},
            )
        return self.get_by_id(id=data_column.id)
