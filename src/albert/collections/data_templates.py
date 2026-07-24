from collections.abc import Iterator
from itertools import islice

from pydantic import Field, validate_call

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator, MetadataPreservingIterator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import DataColumnId, DataTemplateId, UserId
from albert.core.shared.models.patch import (
    GeneralPatchDatum,
    GeneralPatchPayload,
    PGPatchDatum,
    PGPatchPayload,
)
from albert.core.utils import ensure_list
from albert.exceptions import AlbertHTTPError
from albert.resources.data_templates import (
    CurveExample,
    DataColumnValue,
    DataTemplate,
    DataTemplateSearchItem,
    ImageExample,
    ParameterValue,
)
from albert.resources.parameter_groups import DataType, EnumValidationValue, ValueValidation
from albert.utils._patch import (
    build_acl_patch_payload,
    create_data_columns_with_enums,
    create_parameters_with_enums,
    generate_data_template_patches,
)
from albert.utils.data_template import (
    build_curve_example,
    build_image_example,
    get_target_data_column,
)

DEFAULT_ADDITIONAL_FIELDS = [
    "acl",
    "createdAt",
    "createdByName",
    "metadata",
    "owner",
    "tags",
    "standards",
    "team",
]


class DCPatchDatum(PGPatchPayload):
    data: list[GeneralPatchDatum] = Field(
        default_factory=list,
        description="The data to be updated in the data column.",
    )


class DataTemplateCollection(BaseCollection):
    """Manage Data Templates in the Albert platform.

    A Data Template (DAT, IDs formatted ``DAT...``) defines what a test captures. It
    has two parts:

    - ``data_column_values``: the measured RESULTS of the test (its data columns, also
      called "direct variables"). See [`DataColumnValue`][albert.resources.data_templates.DataColumnValue]
      and [`DataColumn`][albert.resources.data_columns.DataColumn].
    - ``parameter_values``: the CONDITIONS under which the test is run (also called
      "indirect variables"). See [`ParameterValue`][albert.resources.parameter_groups.ParameterValue]
      and the Parameter collection.

    A Data Template does not itself store measured values; those live as Property Data.
    When a Data Template is paired with a Workflow inside a Block, only its parameters
    (not its result columns) flow into the Workflow's setpoints.

    This collection is accessed as ``client.data_templates``.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        dt = client.data_templates.get_by_id(id="DAT1")
        print(dt.name)
        # 'Tensile Strength Test'
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for data template requests.

    Methods
    -------
    create(data_template) -> DataTemplate
        Create a new data template, including its data columns and parameters.
    get_by_id(id) -> DataTemplate
        Get a single fully populated template by its ID.
    get_by_ids(ids) -> list[DataTemplate]
        Get many templates by their IDs in batches.
    get_by_name(name) -> DataTemplate | None
        Get a single template by exact (case-insensitive) name, or None.
    search(...) -> Iterator[DataTemplateSearchItem]
        Fast, lightweight search returning partial items (best for lookups/counts).
    get_all(...) -> Iterator[DataTemplate]
        Same filters as search, but returns fully populated templates (slower).
    add_data_columns(data_template_id, data_columns) -> DataTemplate
        Attach result data columns to an existing template.
    add_parameters(data_template_id, parameters) -> DataTemplate
        Attach condition parameters to an existing template.
    update(data_template) -> DataTemplate
        Update an existing template.
    delete(id) -> None
        Delete a template by its ID.
    set_curve_example(data_template_id, example, ...) -> DataTemplate
        Set the example row for a curve data column (shown on the details page).
    set_image_example(data_template_id, example, ...) -> DataTemplate
        Set the example row for an image data column (shown on the details page).
    """

    _api_version = "v3"
    _updatable_attributes = {"name", "description", "metadata"}

    def __init__(self, *, session: AlbertSession):
        """Initialize a DataTemplateCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{DataTemplateCollection._api_version}/datatemplates"

    def create(self, *, data_template: DataTemplate) -> DataTemplate:
        """Create a new data template.

        Creates the template along with its result data columns
        (``data_column_values``) and condition parameters (``parameter_values``).
        Parameters are attached in a follow-up request after the template itself is
        created.

        !!! example
            ```python
            from albert.resources.data_templates import DataTemplate, DataColumnValue
            template = DataTemplate(
                name="Tensile Strength Test",
                data_column_values=[DataColumnValue(data_column_id="DAC1")],
            )
            created = client.data_templates.create(data_template=template)
            created.id
            # 'DAT1'
            ```

        Parameters
        ----------
        data_template : DataTemplate
            The template to create. ``name`` is required. Populate
            ``data_column_values`` with the results the test captures and
            ``parameter_values`` with the conditions under which it is run.

        Returns
        -------
        DataTemplate
            The newly created template, populated with its assigned Data Template ID.
        """
        # Preprocess data_column_values to set validation to None if it is an empty list
        # Handle a bug in the API where validation is an empty list
        # https://support.albertinvent.com/hc/en-us/requests/9177
        if (
            isinstance(data_template.data_column_values, list)
            and len(data_template.data_column_values) == 0
        ):
            data_template.data_column_values = None
        if data_template.data_column_values is not None:
            for column_value in data_template.data_column_values:
                if isinstance(column_value.validation, list) and len(column_value.validation) == 0:
                    column_value.validation = None
        # remove them on the initial post
        parameter_values = data_template.parameter_values
        data_template.parameter_values = None
        response = self.session.post(
            self.base_path,
            json=data_template.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        dt = DataTemplate(**response.json())
        dt.parameter_values = parameter_values
        if parameter_values is None or len(parameter_values) == 0:
            return dt
        else:
            return self.add_parameters(data_template_id=dt.id, parameters=parameter_values)

    @validate_call
    def get_by_id(self, *, id: DataTemplateId) -> DataTemplate:
        """Get a single, fully populated data template by its ID.

        For retrieving many templates at once, use [`get_by_ids`][albert.collections.data_templates.DataTemplateCollection.get_by_ids]. To find
        templates without knowing their IDs, use [`search`][albert.collections.data_templates.DataTemplateCollection.search] or [`get_all`][albert.collections.data_templates.DataTemplateCollection.get_all].

        !!! example
            ```python
            dt = client.data_templates.get_by_id(id="DAT1")
            dt.name
            # 'Tensile Strength Test'
            ```

        Parameters
        ----------
        id : DataTemplateId
            The Data Template ID (format ``DAT...``, e.g. ``"DAT1"``).

        Returns
        -------
        DataTemplate
            The fully populated template.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return DataTemplate(**response.json())

    @validate_call
    def get_by_ids(self, *, ids: list[DataTemplateId]) -> list[DataTemplate]:
        """Get multiple fully populated data templates by their IDs.

        Requests are automatically split into batches, so arbitrarily long ID lists
        are supported.

        !!! example
            ```python
            templates = client.data_templates.get_by_ids(ids=["DAT1", "DAT2"])
            [t.name for t in templates]
            # ['Tensile Strength Test', 'Melt Flow Index']
            ```

        Parameters
        ----------
        ids : list[DataTemplateId]
            The Data Template IDs to retrieve (format ``DAT...``).

        Returns
        -------
        list[DataTemplate]
            The matching templates.
        """
        url = f"{self.base_path}/ids"
        batches = [ids[i : i + 250] for i in range(0, len(ids), 250)]
        return [
            DataTemplate(**item)
            for batch in batches
            for item in self.session.get(url, params={"id": batch}).json()["Items"]
        ]

    def get_by_name(self, *, name: str) -> DataTemplate | None:
        """Get a single, fully populated data template by its exact name.

        The match is case-insensitive. If multiple templates share the name, the
        first match is returned. Returns None when no template matches.

        !!! example
            ```python
            dt = client.data_templates.get_by_name(name="Tensile Strength Test")
            dt.id if dt else "no match"
            # 'DAT1'
            ```

        Parameters
        ----------
        name : str
            The exact name of the data template to retrieve.

        Returns
        -------
        DataTemplate or None
            The matching template, or None if not found.
        """
        for t in self.search(name=name):
            if t.name.lower() == name.lower():
                return t.hydrate()
        return None

    @validate_call
    def add_data_columns(
        self, *, data_template_id: DataTemplateId, data_columns: list[DataColumnValue]
    ) -> DataTemplate:
        """Add result data columns to an existing data template.

        Data columns are the measured results the test captures (its "direct
        variables"). Any enum validations declared on the columns are created as part
        of this call.

        !!! example
            ```python
            from albert.resources.data_templates import DataColumnValue
            updated = client.data_templates.add_data_columns(
                data_template_id="DAT1",
                data_columns=[DataColumnValue(data_column_id="DAC1")],
            )
            ```

        Parameters
        ----------
        data_template_id : DataTemplateId
            The Data Template ID to add the columns to (format ``DAT...``).
        data_columns : list[DataColumnValue]
            The result columns to add. See
            [`DataColumnValue`][albert.resources.data_templates.DataColumnValue].

        Returns
        -------
        DataTemplate
            The updated template, re-fetched with the new columns.
        """
        data_template_url = f"{self.base_path}/{data_template_id}"
        create_data_columns_with_enums(
            session=self.session,
            data_columns_base_url=f"{data_template_url}/datacolumns",
            data_template_url=data_template_url,
            data_columns=data_columns,
        )
        return self.get_by_id(id=data_template_id)

    @validate_call
    def add_parameters(
        self, *, data_template_id: DataTemplateId, parameters: list[ParameterValue]
    ) -> DataTemplate:
        """Add condition parameters to an existing data template.

        Parameters are the conditions under which the test is run (its "indirect
        variables"), and are what flow into a Workflow's setpoints when the template is
        used in a Block. Any enum validations declared on the parameters are created as
        part of this call.

        !!! example
            ```python
            from albert.resources.parameter_groups import ParameterValue
            updated = client.data_templates.add_parameters(
                data_template_id="DAT1",
                parameters=[ParameterValue(id="PRM1", value="25")],
            )
            ```

        Parameters
        ----------
        data_template_id : DataTemplateId
            The Data Template ID to add the parameters to (format ``DAT...``).
        parameters : list[ParameterValue]
            The parameters to add. See
            [`ParameterValue`][albert.resources.parameter_groups.ParameterValue].

        Returns
        -------
        DataTemplate
            The updated template, re-fetched with the new parameters.
        """
        if parameters is None or len(parameters) == 0:
            return self.get_by_id(id=data_template_id)

        parameters_url = f"{self.base_path}/{data_template_id}/parameters"
        create_parameters_with_enums(
            session=self.session,
            parameters_base_url=parameters_url,
            patch_url=parameters_url,
            parameters=parameters,
        )
        return self.get_by_id(id=data_template_id)

    @validate_call
    def search(
        self,
        *,
        name: str | None = None,
        user_id: UserId | None = None,
        owner: str | list[str] | None = None,
        tags: str | list[str] | None = None,
        data_columns: str | list[str] | None = None,
        standard_organization: str | list[str] | None = None,
        additional_field: str | list[str] | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        max_items: int | None = None,
        offset: int | None = 0,
    ) -> Iterator[DataTemplateSearchItem]:
        """Search for data templates matching the given filters.

        This is the fast path: it returns partial (unhydrated)
        [`DataTemplateSearchItem`][albert.resources.data_templates.DataTemplateSearchItem] entities and is
        best for lookups, counts, and pulling IDs. To retrieve fully populated
        templates, use [`get_all`][albert.collections.data_templates.DataTemplateCollection.get_all] instead. Results are returned lazily as an
        iterator that pages through the API on demand.

        !!! example
            ```python
            for item in client.data_templates.search(name="Tensile", max_items=10):
                print(item.id, item.name)
            ```

        Parameters
        ----------
        name : str, optional
            Filter by data template name (text match).
        user_id : UserId, optional
            Filter by the ID of an associated user.
        owner : str or list[str], optional
            Filter by owner name(s).
        tags : str or list[str], optional
            Filter by tag name(s).
        data_columns : str or list[str], optional
            Filter by data column name(s).
        standard_organization : str or list[str], optional
            Filter by standards organization name(s).
        additional_field : str or list[str], optional
            Additional fields to include on each returned item. If omitted, a default
            set of fields is requested.
        order_by : OrderBy, optional
            The order in which to sort results. Default is ``DESCENDING``.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matching items.

        Returns
        -------
        Iterator[DataTemplateSearchItem]
            A lazy iterator of matching partial templates. Call
            `hydrate()` on an
            item to fetch its full [`DataTemplate`][albert.resources.data_templates.DataTemplate].
        """
        payload = {
            "offset": offset,
            "order": order_by,
            "text": name,
            "userId": user_id,
            "owner": ensure_list(owner),
            "tags": ensure_list(tags),
            "dataColumns": ensure_list(data_columns),
            "standardOrganization": ensure_list(standard_organization),
            "additionalField": (
                ensure_list(additional_field)
                if additional_field is not None
                else list(DEFAULT_ADDITIONAL_FIELDS)
            ),
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            method="POST",
            json=payload,
            max_items=max_items,
            deserialize=lambda items: [
                DataTemplateSearchItem.model_validate(x)._bind_collection(self) for x in items
            ],
        )

    def update(self, *, data_template: DataTemplate) -> DataTemplate:
        """Update an existing data template.

        Only the fields listed in Notes are applied. New data columns and parameters
        present on the supplied template (including their enum validations) are
        created as part of this call.

        !!! example
            ```python
            dt = client.data_templates.get_by_id(id="DAT1")
            dt.description = "Updated per ASTM D638"
            updated = client.data_templates.update(data_template=dt)
            ```

        Parameters
        ----------
        data_template : DataTemplate
            The template to update. Its ``id`` must be set and match the template to
            update. Retrieve it with [`get_by_id`][albert.collections.data_templates.DataTemplateCollection.get_by_id], modify the fields listed in
            Notes, then pass it here.

        Returns
        -------
        DataTemplate
            The updated template.

        Notes
        -----
        The following fields can be updated: ``name``, ``description``, and
        ``metadata`` on the template itself, and per-parameter ``value``, ``unit``,
        ``required``, and ``validation``.

        Warnings
        --------
        Only scalar data column values (text, number, dropdown) can be updated with
        this method. Use [`set_curve_example`][albert.collections.data_templates.DataTemplateCollection.set_curve_example] or [`set_image_example`][albert.collections.data_templates.DataTemplateCollection.set_image_example] to set
        example values for curve and image data column types.
        """

        existing = self.get_by_id(id=data_template.id)

        base_payload = self._generate_patch_payload(existing=existing, updated=data_template)

        path = f"{self.base_path}/{existing.id}"
        (
            general_patches,
            new_data_columns,
            data_column_enum_patches,
            new_parameters,
            parameter_enum_patches,
            parameter_patches,
            acl_add_values,
            acl_delete_values,
        ) = generate_data_template_patches(
            initial_patches=base_payload,
            updated_data_template=data_template,
            existing_data_template=existing,
        )

        if len(new_data_columns) > 0:
            create_data_columns_with_enums(
                session=self.session,
                data_columns_base_url=f"{path}/datacolumns",
                data_template_url=path,
                data_columns=new_data_columns,
            )
        existing_columns_by_sequence = {
            x.sequence: x for x in (existing.data_column_values or []) if x.sequence is not None
        }
        if len(data_column_enum_patches) > 0:
            for sequence, enum_patches in data_column_enum_patches.items():
                if len(enum_patches) == 0:
                    continue
                existing_column = existing_columns_by_sequence.get(sequence)
                has_existing_enum_validation = (
                    existing_column is not None
                    and existing_column.validation is not None
                    and len(existing_column.validation) > 0
                    and existing_column.validation[0].datatype == DataType.ENUM
                )
                if not has_existing_enum_validation:
                    continue
                self.session.put(
                    f"{self.base_path}/{existing.id}/datacolumns/{sequence}/enums",
                    json=enum_patches,  # these are simple dicts for now
                )
        if len(new_parameters) > 0:
            parameters_url = f"{path}/parameters"
            create_parameters_with_enums(
                session=self.session,
                parameters_base_url=parameters_url,
                patch_url=parameters_url,
                parameters=new_parameters,
            )
        enum_sequences = {}
        if len(parameter_enum_patches) > 0:
            for sequence, enum_patches in parameter_enum_patches.items():
                if len(enum_patches) == 0:
                    continue

                enums = self.session.put(
                    f"{self.base_path}/{existing.id}/parameters/{sequence}/enums",
                    json=enum_patches,  # these are simple dicts for now
                )
                enum_sequences[sequence] = [EnumValidationValue(**x) for x in enums.json()]

        # Create validation patches ONLY for sequences that actually have enum changes
        enum_validation_patches = []
        for sequence, enums in enum_sequences.items():
            # Only create validation patch if there were actual enum changes
            if len(enums) > 0:
                enum_validation = ValueValidation(
                    datatype=DataType.ENUM,
                    value=enums,
                )
                enum_patch = PGPatchDatum(
                    rowId=sequence,
                    operation="update",
                    attribute="validation",
                    new_value=[enum_validation],
                )
                enum_validation_patches.append(enum_patch)

        # Combine all parameter patches to avoid duplicates
        all_parameter_patches = []

        if len(parameter_patches) > 0:
            patches_by_sequence = {}
            for p in parameter_patches:
                if p.rowId not in patches_by_sequence:
                    patches_by_sequence[p.rowId] = []
                patches_by_sequence[p.rowId].append(p)

            for sequence, patches in patches_by_sequence.items():
                # Filter out validation patches for sequences that have enum sequences
                # because enum validation patches will handle validation for those sequences
                if sequence in enum_sequences:
                    patches = [p for p in patches if p.attribute != "validation"]

                all_parameter_patches.extend(patches)

                # Add enum validation patches (these replace any filtered validation patches)
        # Don't add enum validation patches to all_parameter_patches - apply them separately

        # Apply all parameter patches in one request to avoid duplicates
        if len(all_parameter_patches) > 0:
            # Apply enum validation patches one by one to avoid duplicate validation errors
            for patch in enum_validation_patches:
                single_payload = PGPatchPayload(data=[patch])
                single_json = single_payload.model_dump(
                    mode="json", by_alias=True, exclude_none=True
                )
                self.session.patch(path + "/parameters", json=single_json)

            # Apply non-enum patches if any
            non_enum_patches = [
                p for p in all_parameter_patches if p not in enum_validation_patches
            ]
            if len(non_enum_patches) > 0:
                payload = PGPatchPayload(data=non_enum_patches)
                json_payload = payload.model_dump(mode="json", by_alias=True, exclude_none=True)
                self.session.patch(
                    path + "/parameters",
                    json=json_payload,
                )

        acl_add_payload = build_acl_patch_payload(operation="add", values=acl_add_values)
        if acl_add_payload is not None:
            self.session.patch(
                path,
                json=acl_add_payload.model_dump(mode="json", by_alias=True, exclude_none=True),
            )

        acl_delete_payload = build_acl_patch_payload(operation="delete", values=acl_delete_values)
        if acl_delete_payload is not None:
            self.session.patch(
                path,
                json=acl_delete_payload.model_dump(mode="json", by_alias=True, exclude_none=True),
            )

        if len(general_patches.data) > 0:
            payload = GeneralPatchPayload(data=general_patches.data)
            self.session.patch(
                path,
                json=payload.model_dump(mode="json", by_alias=True, exclude_none=True),
            )
        return self.get_by_id(id=data_template.id)

    @validate_call
    def delete(self, *, id: DataTemplateId) -> None:
        """Delete a data template by its ID.

        !!! example
            ```python
            client.data_templates.delete(id="DAT1")
            ```

        Parameters
        ----------
        id : DataTemplateId
            The Data Template ID to delete (format ``DAT...``).

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
        user_id: UserId | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        max_items: int | None = None,
        offset: int | None = 0,
    ) -> Iterator[DataTemplate]:
        """Get fully populated data templates matching the given filters.

        This mirrors [`search`][albert.collections.data_templates.DataTemplateCollection.search] but hydrates each match into a complete
        [`DataTemplate`][albert.resources.data_templates.DataTemplate] (via [`get_by_ids`][albert.collections.data_templates.DataTemplateCollection.get_by_ids]), so it is slower. Use
        [`search`][albert.collections.data_templates.DataTemplateCollection.search] when you only need lightweight, partial entities. Results are
        returned lazily as an iterator that pages through the API on demand.

        !!! example
            ```python
            for dt in client.data_templates.get_all(name="Tensile", max_items=10):
                print(dt.id, dt.name)
            ```

        Parameters
        ----------
        name : str, optional
            Filter by data template name (text match).
        user_id : UserId, optional
            Filter by the ID of an associated user.
        order_by : OrderBy, optional
            The order in which to sort results. Default is ``DESCENDING``.
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matching items.

        Returns
        -------
        Iterator[DataTemplate]
            A lazy iterator over fully populated templates. Preserves ``has_more`` /
            ``total`` from the underlying search paginator.
        """
        source = self.search(
            name=name,
            user_id=user_id,
            order_by=order_by,
            max_items=max_items,
            offset=offset,
        )

        def _hydrated() -> Iterator[DataTemplate]:
            it = (item.id for item in source)
            while batch := list(islice(it, 100)):
                try:
                    yield from self.get_by_ids(ids=batch)
                except AlbertHTTPError as e:
                    logger.warning(f"Error hydrating batch {batch}: {e}")

        return MetadataPreservingIterator(source, _hydrated())

    @validate_call
    def set_curve_example(
        self,
        *,
        data_template_id: DataTemplateId,
        data_column_id: DataColumnId | None = None,
        data_column_name: str | None = None,
        example: CurveExample,
    ) -> DataTemplate:
        """Set the example row for a curve data column.

        An example row is a sample value displayed only on the Data Template details
        page (it is not shown in tasks and is not measured Property Data). Curve
        columns get a dedicated helper because a curve is a complex type sourced from a
        CSV file or an existing attachment. Identify the target column by exactly one
        of ``data_column_id`` or ``data_column_name``.

        !!! example
            ```python
            from albert.resources.data_templates import CurveExample
            updated = client.data_templates.set_curve_example(
                data_template_id="DAT1",
                data_column_name="Viscosity Curve",
                example=CurveExample(file_path="curve.csv"),
            )
            ```

        Parameters
        ----------
        data_template_id : DataTemplateId
            The Data Template ID that owns the column (format ``DAT...``).
        data_column_id : DataColumnId, optional
            The target curve column's ID. Provide exactly one of ``data_column_id`` or
            ``data_column_name``.
        data_column_name : str, optional
            The target curve column's name. Provide exactly one of ``data_column_id``
            or ``data_column_name``.
        example : CurveExample
            The curve example to apply. See
            [`CurveExample`][albert.resources.data_templates.CurveExample].

        Returns
        -------
        DataTemplate
            The updated template, re-fetched after the example is applied.
        """
        data_template = self.get_by_id(id=data_template_id)
        target_column = get_target_data_column(
            data_template=data_template,
            data_template_id=data_template_id,
            data_column_id=data_column_id,
            data_column_name=data_column_name,
        )
        payload = build_curve_example(
            session=self.session,
            data_template_id=data_template_id,
            example=example,
            target_column=target_column,
        )
        if not payload.data:
            return data_template
        self.session.patch(
            f"{self.base_path}/{data_template_id}",
            json=payload.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return self.get_by_id(id=data_template_id)

    @validate_call
    def set_image_example(
        self,
        *,
        data_template_id: DataTemplateId,
        data_column_id: DataColumnId | None = None,
        data_column_name: str | None = None,
        example: ImageExample,
    ) -> DataTemplate:
        """Set the example row for an image data column.

        An example row is a sample value displayed only on the Data Template details
        page (it is not shown in tasks and is not measured Property Data). Image
        columns get a dedicated helper because an image is a complex type sourced from
        a local file. Identify the target column by exactly one of ``data_column_id``
        or ``data_column_name``.

        !!! example
            ```python
            from albert.resources.data_templates import ImageExample
            updated = client.data_templates.set_image_example(
                data_template_id="DAT1",
                data_column_name="Fracture Surface",
                example=ImageExample(file_path="fracture.png"),
            )
            ```

        Parameters
        ----------
        data_template_id : DataTemplateId
            The Data Template ID that owns the column (format ``DAT...``).
        data_column_id : DataColumnId, optional
            The target image column's ID. Provide exactly one of ``data_column_id`` or
            ``data_column_name``.
        data_column_name : str, optional
            The target image column's name. Provide exactly one of ``data_column_id``
            or ``data_column_name``.
        example : ImageExample
            The image example to apply. See
            [`ImageExample`][albert.resources.data_templates.ImageExample].

        Returns
        -------
        DataTemplate
            The updated template, re-fetched after the example is applied.
        """
        data_template = self.get_by_id(id=data_template_id)
        target_column = get_target_data_column(
            data_template=data_template,
            data_template_id=data_template_id,
            data_column_id=data_column_id,
            data_column_name=data_column_name,
        )
        payload = build_image_example(
            session=self.session,
            data_template_id=data_template_id,
            example=example,
            target_column=target_column,
        )
        if not payload.data:
            return data_template
        self.session.patch(
            f"{self.base_path}/{data_template_id}",
            json=payload.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return self.get_by_id(id=data_template_id)
