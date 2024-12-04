import json
from collections.abc import Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.data_columns import DataColumn
from albert.session import AlbertSession
from albert.utils.pagination import AlbertPaginator, PaginationMode


class DataColumnCollection(BaseCollection):
    """A collection for interacting with Data Columns in Albert."""

    _api_version = "v3"
    _updatable_attributes = {"name"}

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

    def get_by_id(self, *, id) -> DataColumn | None:
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
        limit: int = 100,
        order_by: OrderBy = OrderBy.DESCENDING,
        ids: str | list[str] | None = None,
        name: str | list[str] | None = None,
        exact_match: bool | None = None,
        default: bool | None = None,
        start_key: str | None = None,
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

        Returns
        -------
        Iterator[DataColumn]
            An iterator of DataColumns.
        """
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
            deserialize=lambda items: [DataColumn(**item) for item in items],
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

    def update(self, *, data_column: DataColumn) -> DataColumn:
        """
        Update a data column entity.

        Parameters
        ----------
        data_column : DataColumn
            The data column object to update.

        Returns
        -------
        DataColumn
            The updated data column object.
        """
        patch_payload = self._generate_patch_payload(
            existing=self.get_by_id(data_column.id),
            updated=data_column,
        )
        self.session.patch(
            f"self.base_path/{data_column.id}",
            json=patch_payload.model_dump(mode="json", by_alias=True),
        )
        return self.get_by_id(id=data_column.id)
