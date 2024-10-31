from collections.abc import Generator, Iterator

from albert.collections.base import BaseCollection, OrderBy
from albert.resources.data_columns import DataColumn
from albert.session import AlbertSession


class DataColumnCollection(BaseCollection):
    """A collection for interacting with Data Columns in Albert."""

    _api_version = "v3"
    _updatable_attributes = {"name"}

    def __init__(self, *, session: AlbertSession):
        """Initialize the DataColumnCollection with the provided session."""
        super().__init__(session=session)
        self.base_path = f"/api/{DataColumnCollection._api_version}/datacolumns"

    def _list_generator(
        self,
        *,
        limit: int = 50,
        order_by: OrderBy = OrderBy.DESCENDING,
        name: str | list[str] = None,
        exact_match: bool | None = None,
        start_key: str | None = None,
        default: bool | None = None,
    ) -> Generator[DataColumn, None, None]:
        """
        Lists tag entities with optional filters.

        Parameters
        ----------
        limit : int, optional
            The maximum number of tags to return, by default 50.
        order_by : OrderBy, optional
            The order by which to sort the results, by default OrderBy.DESCENDING.
        name : Union[str, None], optional
            The name of the tag to filter by, by default None.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.
        start_key : Optional[str], optional
            The starting point for the next set of results, by default None.

        Returns
        -------
        Generator
            A generator of Tag objects.
        """
        params = {
            "limit": limit,
            "orderBy": order_by.value,
            "startKey": start_key,
            "default": default if default is None else str(default).lower(),
            "exactMatch": exact_match if exact_match is None else str(exact_match).lower(),
        }
        if name:
            params["name"] = name if isinstance(name, list) else [name]

        params = {k: v for k, v in params.items() if v is not None}
        while True:
            response = self.session.get(self.base_path, params=params)
            dc_data = response.json().get("Items", [])
            if not dc_data or dc_data == []:
                break
            for dc in dc_data:
                this_dc = DataColumn(**dc)
                yield this_dc
            start_key = response.json().get("lastKey")
            if not start_key:
                break
            params["startKey"] = start_key

    def list(
        self,
        *,
        order_by: OrderBy = OrderBy.DESCENDING,
        name: str | list[str] = None,
        exact_match: bool | None = None,
        default: bool | None = None,
    ) -> Iterator[DataColumn]:
        """
        Lists tag entities with optional filters.

        Parameters
        ----------
        order_by : OrderBy, optional
            The order by which to sort the results, by default OrderBy.DESCENDING.
        name : Union[str, None], optional
            The name of the tag to filter by, by default None.
        exact_match : bool, optional
            Whether to match the name exactly, by default True.
        default : bool, optional
            Whether to return only default columns, by default None.

        Returns
        -------
        Generator
            A generator of Tag objects.
        """
        return self._list_generator(
            order_by=order_by, name=name, exact_match=exact_match, default=default
        )

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
        payload = [data_column.model_dump(by_alias=True, exclude_unset=True)]
        response = self.session.post(self.base_path, json=payload)

        return DataColumn(**response.json()[0])

    def delete(self, *, data_column_id: str) -> None:
        """
        Delete a data column entity.

        Parameters
        ----------
        data_column : DataColumn
            The data column object to delete.
        """
        self.session.delete(f"{self.base_path}/{data_column_id}")
        return None

    def update(self, *, updated_data_column: DataColumn) -> DataColumn:
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
        patch = self._generate_patch_payload(
            existing=self.get_by_id(updated_data_column.id), updated=updated_data_column
        )
        self.session.patch(f"self.base_path/{updated_data_column.id}", json=patch)
        return self.get_by_id(id=updated_data_column.id)
