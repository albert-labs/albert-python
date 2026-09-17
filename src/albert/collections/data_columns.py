import logging
from collections.abc import Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import DataColumnId
from albert.core.utils import ensure_list
from albert.resources.data_columns import DataColumn, DataColumnSearchItem


class DataColumnCollection(BaseCollection):
    """Manage Data Columns in the Albert platform.

    A Data Column (DAC, IDs ``DAC...``) is the definition of a single measured
    result variable, such as ``Viscosity`` or ``APHA Color``. Data columns are the
    reusable building blocks of a Data Template's results: a
    [`DataTemplate`][albert.resources.data_templates.DataTemplate] references them through
    its ``data_column_values``, and the values recorded against a data column
    during experiments are stored as Property Data.

    This collection is accessed as ``client.data_columns``.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        dc = client.data_columns.get_by_id(id="DAC9999999")
        dc.name
        # 'Viscosity'
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for data column requests.

    Methods
    -------
    search(...) -> Iterator[DataColumnSearchItem]
        Search data columns with free text and filters, returning partial items.
    get_all(...) -> Iterator[DataColumn]
        Get data columns matching optional filters.
    get_by_id(id) -> DataColumn
        Get a single data column by its ID.
    get_by_name(name) -> DataColumn | None
        Get a single data column by its exact name.
    create(data_column) -> DataColumn
        Create a new data column.
    get_or_create(data_column) -> DataColumn
        Return the existing data column matching by name, or create it.
    update(data_column) -> DataColumn
        Update an existing data column.
    delete(id) -> None
        Delete a data column by its ID.
    """

    _api_version = "v3"
    _updatable_attributes = {"name", "metadata"}

    def __init__(self, *, session: AlbertSession):
        """Initialize a DataColumnCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{DataColumnCollection._api_version}/datacolumns"

    @validate_call
    def get_by_name(self, *, name: str) -> DataColumn | None:
        """Get a single data column by its exact name.

        Matching is case-insensitive. To retrieve multiple columns or use partial
        matching, use [`get_all`][albert.collections.data_columns.DataColumnCollection.get_all]; for
        free-text search, use [`search`][albert.collections.data_columns.DataColumnCollection.search].

        !!! example
            ```python
            dc = client.data_columns.get_by_name(name="Viscosity")
            dc.id if dc else "no match"
            # 'DAC9999999'
            ```

        Parameters
        ----------
        name : str
            The name of the data column to retrieve (e.g. ``"Viscosity"``).

        Returns
        -------
        DataColumn or None
            The matching data column, or None if no exact match is found.
        """
        for dc in self.get_all(name=name):
            if dc.name.lower() == name.lower():
                return dc
        return None

    @validate_call
    def get_by_id(self, *, id: DataColumnId) -> DataColumn:
        """Get a single data column by its ID.

        To find a column without knowing its ID, use [`get_by_name`][albert.collections.data_columns.DataColumnCollection.get_by_name] or
        [`get_all`][albert.collections.data_columns.DataColumnCollection.get_all].

        !!! example
            ```python
            dc = client.data_columns.get_by_id(id="DAC9999999")
            dc.name
            # 'Viscosity'
            ```

        Parameters
        ----------
        id : DataColumnId
            The Data Column ID (format ``DAC...``, e.g. ``"DAC9999999"``).

        Returns
        -------
        DataColumn
            The fully populated data column.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        dc = DataColumn(**response.json())
        return dc

    @validate_call
    def search(
        self,
        *,
        text: str | None = None,
        created_by: str | list[str] | None = None,
        data_template: str | list[str] | None = None,
        albert_id: str | list[str] | None = None,
        facet_text: str | None = None,
        facet_field: str | None = None,
        contains_field: str | list[str] | None = None,
        contains_text: str | list[str] | None = None,
        source_field: str | list[str] | None = None,
        additional_field: str | list[str] | None = None,
        translation: str | list[str] | None = None,
        sort_by: str | None = None,
        order: OrderBy | None = None,
        metadata_filters: dict[str, Any] | None = None,
        custom_fields: dict[str, Any] | None = None,
        max_items: int | None = None,
    ) -> Iterator[DataColumnSearchItem]:
        """Search for data columns matching the given filters.

        Returns partial (unhydrated)
        [`DataColumnSearchItem`][albert.resources.data_columns.DataColumnSearchItem] entities, best for
        free-text lookups, counts, and pulling IDs. Results are returned lazily as an
        iterator that pages through matches on demand. Call ``hydrate()`` on an item
        to fetch its full [`DataColumn`][albert.resources.data_columns.DataColumn].

        !!! example
            ```python
            for item in client.data_columns.search(text="Viscosity", max_items=10):
                print(item.id, item.name)
            ```

        Parameters
        ----------
        text : str, optional
            Free-text query matched against data column fields.
        created_by : str or list[str], optional
            Filter by creator user ID(s).
        data_template : str or list[str], optional
            Filter by data template name(s) the columns belong to.
        albert_id : str or list[str], optional
            Filter by Data Column ID(s) (format ``DAC...``).
        facet_text : str, optional
            Text to match within a facet search.
        facet_field : str, optional
            Field to search within for facet filtering.
        contains_field : str or list[str], optional
            Field(s) to apply a "contains" search to.
        contains_text : str or list[str], optional
            Text value(s) for the "contains" search.
        source_field : str or list[str], optional
            Restrict which fields are returned on each search hit.
        additional_field : str or list[str], optional
            Additional fields to include on each search hit.
        translation : str or list[str], optional
            Filter by translation(s).
        sort_by : str, optional
            Attribute to sort results by.
        order : OrderBy, optional
            The order in which to sort results (``asc`` or ``desc``).
        metadata_filters : dict[str, Any], optional
            Filter by metadata field values.
        custom_fields : dict[str, Any], optional
            Filter by custom field values.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matching items.

        Returns
        -------
        Iterator[DataColumnSearchItem]
            A lazy iterator of matching partial data columns. Call ``hydrate()`` on an
            item to fetch its full [`DataColumn`][albert.resources.data_columns.DataColumn].
        """
        payload: dict[str, Any] = {
            "text": text,
            "createdBy": ensure_list(created_by),
            "dataTemplate": ensure_list(data_template),
            "albertId": ensure_list(albert_id),
            "facetText": facet_text,
            "facetField": facet_field,
            "containsField": ensure_list(contains_field),
            "containsText": ensure_list(contains_text),
            "sourceField": ensure_list(source_field),
            "additionalField": ensure_list(additional_field),
            "translation": ensure_list(translation),
            "sortBy": sort_by,
            "order": order,
        }
        if metadata_filters is not None:
            payload["metadataFilters"] = {"metadata": metadata_filters}
        if custom_fields is not None:
            payload["customFields"] = {"metadata": custom_fields}

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            method="POST",
            json=payload,
            max_items=max_items,
            deserialize=lambda items: [
                DataColumnSearchItem.model_validate(x)._bind_collection(self) for x in items
            ],
        )

    @validate_call
    def get_all(
        self,
        *,
        order_by: OrderBy = OrderBy.DESCENDING,
        ids: DataColumnId | list[DataColumnId] | None = None,
        name: str | list[str] | None = None,
        exact_match: bool | None = None,
        default: bool | None = None,
        start_key: str | None = None,
        max_items: int | None = None,
    ) -> Iterator[DataColumn]:
        """Get data columns matching the given filters.

        Results are returned as a lazily paginated iterator, so iterating fetches
        additional pages on demand. To retrieve a single column by its exact name,
        use [`get_by_name`][albert.collections.data_columns.DataColumnCollection.get_by_name]; by its ID, use [`get_by_id`][albert.collections.data_columns.DataColumnCollection.get_by_id]. For
        free-text search, use [`search`][albert.collections.data_columns.DataColumnCollection.search].

        !!! example
            ```python
            for dc in client.data_columns.get_all(name="Color", max_items=10):
                print(dc.id, dc.name)
            ```

        Parameters
        ----------
        order_by : OrderBy, optional
            Sort direction. Default ``OrderBy.DESCENDING``.
        ids : DataColumnId or list[DataColumnId], optional
            Filter by one or more Data Column IDs (format ``DAC...``).
        name : str or list[str], optional
            Filter by name(s).
        exact_match : bool, optional
            When True, the ``name`` filter must match exactly; otherwise partial
            matches are included.
        default : bool, optional
            When True, return only default data columns.
        start_key : str, optional
            Pagination key to resume from. Usually left unset.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Returns
        -------
        Iterator[DataColumn]
            A lazily paginated iterator of matching data columns.
        """

        def deserialize(items: list[dict]) -> Iterator[DataColumn]:
            yield from (DataColumn(**item) for item in items)

        params = {
            "orderBy": order_by,
            "startKey": start_key,
            "name": ensure_list(name),
            "exactMatch": exact_match,
            "default": default,
            "dataColumns": ensure_list(ids),
        }

        return AlbertPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=deserialize,
        )

    def create(self, *, data_column: DataColumn) -> DataColumn:
        """Create a new data column.

        To avoid creating a duplicate when a column with the same name may already
        exist, use [`get_or_create`][albert.collections.data_columns.DataColumnCollection.get_or_create] instead.

        !!! example
            ```python
            from albert.resources.data_columns import DataColumn
            created = client.data_columns.create(data_column=DataColumn(name="Viscosity"))
            created.id
            # 'DAC9999999'
            ```

        Parameters
        ----------
        data_column : DataColumn
            The data column to create. ``name`` is required; leave ``id`` unset.

        Returns
        -------
        DataColumn
            The newly created data column, populated with its assigned Data Column ID.
        """
        payload = [data_column.model_dump(by_alias=True, exclude_unset=True, mode="json")]
        response = self.session.post(self.base_path, json=payload)

        return DataColumn(**response.json()[0])

    def get_or_create(self, *, data_column: DataColumn) -> DataColumn:
        """Return the existing data column matching by name, or create it.

        If a data column with the same name already exists, that existing column is
        returned instead of creating a duplicate; otherwise a new column is created
        via [`create`][albert.collections.data_columns.DataColumnCollection.create].

        !!! example
            ```python
            from albert.resources.data_columns import DataColumn
            dc = client.data_columns.get_or_create(data_column=DataColumn(name="Viscosity"))
            dc.id
            # 'DAC9999999'
            ```

        Parameters
        ----------
        data_column : DataColumn
            The data column to get or create. Its ``name`` is used to match.

        Returns
        -------
        DataColumn
            The existing or newly created data column.
        """
        for match in self.get_all(name=data_column.name, exact_match=False):
            if match.name == data_column.name:
                logging.warning(
                    f"DataColumn with name {data_column.name} already exists. Returning existing data column."
                )
                return match
        return self.create(data_column=data_column)

    @validate_call
    def delete(self, *, id: DataColumnId) -> None:
        """Delete a data column by its ID.

        !!! example
            ```python
            client.data_columns.delete(id="DAC9999999")
            ```

        Parameters
        ----------
        id : DataColumnId
            The Data Column ID to delete (format ``DAC...``).

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
        """Update an existing data column.

        Fetch the column (e.g. with [`get_by_id`][albert.collections.data_columns.DataColumnCollection.get_by_id]), modify the updatable fields
        on the returned object, then pass it here. Only the fields listed in Notes
        are applied; changes to other fields are ignored.

        !!! example
            ```python
            dc = client.data_columns.get_by_id(id="DAC9999999")
            dc.name = "Kinematic Viscosity"
            updated = client.data_columns.update(data_column=dc)
            updated.name
            # 'Kinematic Viscosity'
            ```

        Parameters
        ----------
        data_column : DataColumn
            The data column to update. Must have a valid ``id`` matching an existing
            data column.

        Returns
        -------
        DataColumn
            The updated data column as registered in Albert.

        Notes
        -----
        The following fields can be updated: ``metadata``, ``name``.
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
