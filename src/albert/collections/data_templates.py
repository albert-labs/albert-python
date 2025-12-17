from collections.abc import Iterator
from itertools import islice
from pathlib import Path

from pydantic import Field, validate_call

from albert.collections.attachments import AttachmentCollection
from albert.collections.base import BaseCollection
from albert.collections.files import FileCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import AttachmentId, DataColumnId, DataTemplateId, UserId
from albert.core.shared.models.patch import (
    GeneralPatchDatum,
    GeneralPatchPayload,
    PGPatchDatum,
    PGPatchPayload,
)
from albert.exceptions import AlbertHTTPError
from albert.resources.data_templates import (
    DataColumnValue,
    DataTemplate,
    DataTemplateSearchItem,
    ParameterValue,
)
from albert.resources.parameter_groups import DataType, EnumValidationValue, ValueValidation
from albert.resources.tasks import ImportMode
from albert.utils._patch import generate_data_template_patches
from albert.utils.data_template import (
    build_curve_import_patch_payload,
    create_curve_import_job,
    derive_curve_csv_mapping,
    exec_curve_script,
    get_script_attachment,
    get_target_data_column,
    prepare_curve_input_attachment,
    validate_data_column_type,
)
from albert.utils.tasks import CSV_EXTENSIONS, fetch_csv_table_rows


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
    def import_curve_data(
        self,
        *,
        data_template_id: DataTemplateId,
        data_column_id: DataColumnId | None = None,
        data_column_name: str | None = None,
        mode: ImportMode = ImportMode.CSV,
        field_mapping: dict[str, str] | None = None,
        file_path: str | Path | None = None,
        attachment_id: AttachmentId | None = None,
    ) -> DataTemplate:
        """Import curve data in a data template column.

        Parameters
        ----------
        data_template_id : DataTemplateId
            Target data template Id.
        data_column_id : DataColumnId | None, optional
            Specific data column to upload the curve data to. Provide exactly one of ``data_column_id`` or
            ``data_column_name``.
        data_column_name : str | None, optional
            Case-insensitive data column display name. Provide exactly one of the column
            identifier or name.
        mode : ImportMode, optional
            Import mode. ``ImportMode.SCRIPT`` runs the attached automation script and requires
            a script attachment on the data template; ``ImportMode.CSV`` ingests the
            uploaded CSV directly. Defaults to ``ImportMode.CSV``.
        field_mapping : dict[str, str] | None, optional
            Optional manual mapping from CSV headers to curve result column names on the target column. Example: ``{"visc": "Viscosity"}`` maps the
            "visc" CSV header to the "Viscosity" curve result column. Mappings are matched
            case-insensitively and override auto-detection. In ``ImportMode.SCRIPT`` this applies to the headers emitted by the script before ingestion.
        attachment_id : AttachmentId | None, optional
            Existing attachment to use. Exactly one of ``attachment_id`` or ``file_path`` must be provided.
        file_path : str | Path | None, optional
            Local file to upload and attach to a new note on the data template. Exactly one of
            ``attachment_id`` or ``file_path`` must be provided.
        Returns
        -------
        DataTemplate
            The data template refreshed after the curve import job completes.

        Examples
        --------
        !!! example "Import curve data from a CSV file"
            ```python
            dt = client.data_templates.import_curve_data(
                data_template_id="DT123",
                data_column_name="APHA Color",
                mode=ImportMode.CSV,
                file_path="path/to/curve.csv",
                field_mapping={"visc": "Viscosity"},
            )
            ```
        """
        data_template = self.get_by_id(id=data_template_id)
        target_column = get_target_data_column(
            data_template=data_template,
            data_template_id=data_template_id,
            data_column_id=data_column_id,
            data_column_name=data_column_name,
        )
        validate_data_column_type(target_column=target_column)
        column_id = target_column.data_column_id
        attachment_collection = AttachmentCollection(session=self.session)

        script_attachment_signed_url: str | None = None

        if mode is ImportMode.SCRIPT:
            script_attachment, script_extensions = get_script_attachment(
                attachment_collection=attachment_collection,
                data_template_id=data_template_id,
                column_id=column_id,
            )
            if not script_extensions:
                raise ValueError("Script attachment must define allowed extensions.")
            script_attachment_signed_url = script_attachment.signed_url
            allowed_extensions = set(script_extensions)
        else:
            allowed_extensions = set(CSV_EXTENSIONS)
        raw_attachment = prepare_curve_input_attachment(
            attachment_collection=attachment_collection,
            data_template_id=data_template_id,
            column_id=column_id,
            allowed_extensions=allowed_extensions,
            file_path=file_path,
            attachment_id=attachment_id,
            require_signed_url=mode is ImportMode.SCRIPT,
        )
        raw_key = raw_attachment.key
        if raw_attachment.id is None:
            raise ValueError("Curve input attachment did not return an identifier.")
        resolved_attachment_id = AttachmentId(raw_attachment.id)

        processed_input_key: str = raw_key
        column_headers: dict[str, str] = {}

        if mode is ImportMode.SCRIPT:
            file_collection = FileCollection(session=self.session)
            processed_input_key, column_headers = exec_curve_script(
                session=self.session,
                api_version=self._api_version,
                data_template_id=data_template_id,
                column_id=column_id,
                raw_attachment=raw_attachment,
                file_collection=file_collection,
                script_attachment_signed_url=script_attachment_signed_url,
            )
        else:
            table_rows = fetch_csv_table_rows(
                session=self.session,
                attachment_id=resolved_attachment_id,
                headers_only=True,
            )
            header_row = table_rows[0]
            if not isinstance(header_row, dict):
                raise ValueError("Unexpected CSV header format returned by preview endpoint.")
            column_headers = {
                key: value
                for key, value in header_row.items()
                if isinstance(key, str) and isinstance(value, str) and value
            }

        csv_mapping = derive_curve_csv_mapping(
            target_column=target_column,
            column_headers=column_headers,
            field_mapping=field_mapping,
        )

        job_id, partition_uuid, s3_output_key = create_curve_import_job(
            session=self.session,
            data_template_id=data_template_id,
            column_id=column_id,
            csv_mapping=csv_mapping,
            raw_attachment=raw_attachment,
            processed_input_key=processed_input_key,
        )

        patch_payload = build_curve_import_patch_payload(
            target_column=target_column,
            job_id=job_id,
            csv_mapping=csv_mapping,
            raw_attachment=raw_attachment,
            partition_uuid=partition_uuid,
            s3_output_key=s3_output_key,
        )
        self.session.patch(
            f"{self.base_path}/{data_template_id}",
            json=patch_payload.model_dump(by_alias=True, mode="json", exclude_none=True),
        )

        return self.get_by_id(id=data_template_id)

    def _add_param_enums(
        self,
        *,
        data_template_id: DataTemplateId,
        new_parameters: list[ParameterValue],
    ) -> list[EnumValidationValue]:
        """Adds enum values to a parameter."""

        data_template = self.get_by_id(id=data_template_id)
        existing_parameters = data_template.parameter_values
        enums_by_sequence = {}
        for parameter in new_parameters:
            this_sequence = next(
                (
                    p.sequence
                    for p in existing_parameters
                    if p.id == parameter.id and p.short_name == parameter.short_name
                ),
                None,
            )
            enum_patches = []
            if (
                parameter.validation
                and len(parameter.validation) > 0
                and isinstance(parameter.validation[0].value, list)
            ):
                existing_validation = (
                    [x for x in existing_parameters if x.sequence == parameter.sequence]
                    if existing_parameters
                    else []
                )
                existing_enums = (
                    [
                        x
                        for x in existing_validation[0].validation[0].value
                        if isinstance(x, EnumValidationValue) and x.id is not None
                    ]
                    if (
                        existing_validation
                        and len(existing_validation) > 0
                        and existing_validation[0].validation
                        and len(existing_validation[0].validation) > 0
                        and existing_validation[0].validation[0].value
                        and isinstance(existing_validation[0].validation[0].value, list)
                    )
                    else []
                )
                updated_enums = (
                    [
                        x
                        for x in parameter.validation[0].value
                        if isinstance(x, EnumValidationValue)
                    ]
                    if parameter.validation[0].value
                    else []
                )

                deleted_enums = [
                    x for x in existing_enums if x.id not in [y.id for y in updated_enums]
                ]

                new_enums = [
                    x for x in updated_enums if x.id not in [y.id for y in existing_enums]
                ]

                matching_enums = [
                    x for x in updated_enums if x.id in [y.id for y in existing_enums]
                ]

                for new_enum in new_enums:
                    enum_patches.append({"operation": "add", "text": new_enum.text})
                for deleted_enum in deleted_enums:
                    enum_patches.append({"operation": "delete", "id": deleted_enum.id})
                for matching_enum in matching_enums:
                    if (
                        matching_enum.text
                        != [x for x in existing_enums if x.id == matching_enum.id][0].text
                    ):
                        enum_patches.append(
                            {
                                "operation": "update",
                                "id": matching_enum.id,
                                "text": matching_enum.text,
                            }
                        )

                if len(enum_patches) > 0:
                    enum_response = self.session.put(
                        f"{self.base_path}/{data_template_id}/parameters/{this_sequence}/enums",
                        json=enum_patches,
                    )
                    enums_by_sequence[this_sequence] = [
                        EnumValidationValue(**x) for x in enum_response.json()
                    ]
        return enums_by_sequence

    @validate_call
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

    @validate_call
    def get_by_ids(self, *, ids: list[DataTemplateId]) -> list[DataTemplate]:
        """Get a list of data templates by their IDs.

        Parameters
        ----------
        ids : list[DataTemplateId]
            The list of DataTemplate IDs to get.

        Returns
        -------
        list[DataTemplate]
            A list of DataTemplate entities with the provided IDs.
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
        for t in self.search(name=name):
            if t.name.lower() == name.lower():
                return t.hydrate()
        return None

    @validate_call
    def add_data_columns(
        self, *, data_template_id: DataTemplateId, data_columns: list[DataColumnValue]
    ) -> DataTemplate:
        """Adds data columns to a data template.

        Parameters
        ----------
        data_template_id : str
            The ID of the data template to add the columns to.
        data_columns : list[DataColumnValue]
            The list of DataColumnValue entities to add to the data template.

        Returns
        -------
        DataTemplate
            The updated DataTemplate object.
        """
        # if there are enum values, we need to add them as an allowed enum
        for column in data_columns:
            if (
                column.validation
                and len(column.validation) > 0
                and isinstance(column.validation[0].value, list)
            ):
                for enum_value in column.validation[0].value:
                    self.session.put(
                        f"{self.base_path}/{data_template_id}/datacolumns/{column.sequence}/enums",
                        json=[
                            enum_value.model_dump(mode="json", by_alias=True, exclude_none=True)
                        ],
                    )

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

    @validate_call
    def add_parameters(
        self, *, data_template_id: DataTemplateId, parameters: list[ParameterValue]
    ) -> DataTemplate:
        """Adds parameters to a data template.

        Parameters
        ----------
        data_template_id : str
            The ID of the data template to add the columns to.
        parameters : list[ParameterValue]
            The list of ParameterValue entities to add to the data template.

        Returns
        -------
        DataTemplate
            The updated DataTemplate object.
        """
        # make sure the parameter values have a default validaion of string type.
        initial_enum_values = {}  # use parameter ID to track the enum values
        cleaned_params = []
        if parameters is None or len(parameters) == 0:
            return self.get_by_id(id=data_template_id)
        for param in parameters:
            if (
                param.validation
                and len(param.validation) > 0
                and param.validation[0].datatype == DataType.ENUM
            ):
                initial_enum_values[param.id] = param.validation[0].value
                param.validation[0].value = None
                param.validation[0].datatype = DataType.STRING
            cleaned_params.append(param)

        payload = {
            "Parameters": [
                x.model_dump(mode="json", by_alias=True, exclude_none=True) for x in cleaned_params
            ]
        }
        # if there are enum values, we need to add them as an allowed enum
        response = self.session.put(
            f"{self.base_path}/{data_template_id}/parameters",
            json=payload,
        )
        returned_parameters = [ParameterValue(**x) for x in response.json()["Parameters"]]
        for param in returned_parameters:
            if param.id in initial_enum_values:
                param.validation[0].value = initial_enum_values[param.id]
                param.validation[0].datatype = DataType.ENUM
                self._add_param_enums(
                    data_template_id=data_template_id,
                    new_parameters=[param],
                )

        return self.get_by_id(id=data_template_id)

    @validate_call
    def search(
        self,
        *,
        name: str | None = None,
        user_id: UserId | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        max_items: int | None = None,
        offset: int | None = 0,
    ) -> Iterator[DataTemplateSearchItem]:
        """
        Search for DataTemplate matching the provided criteria.

        ⚠️ This method returns partial (unhydrated) entities to optimize performance.
        To retrieve fully detailed entities, use `get_all` instead.

        Parameters
        ----------
        name : str, optional
            The name of the data template to filter by.
        user_id : str, optional
            The user ID to filter by.
        order_by : OrderBy, optional
            The order in which to sort the results. Default is DESCENDING.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.
        offset : int, optional
            The result offset to begin pagination from.

        Returns
        -------
        Iterator[DataTemplateSearchItem]
            An iterator of matching DataTemplateSearchItem entities.
        """
        params = {
            "offset": offset,
            "order": order_by.value,
            "text": name,
            "userId": user_id,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [
                DataTemplateSearchItem.model_validate(x)._bind_collection(self) for x in items
            ],
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
        (
            general_patches,
            new_data_columns,
            data_column_enum_patches,
            new_parameters,
            parameter_enum_patches,
            parameter_patches,
        ) = generate_data_template_patches(
            initial_patches=base_payload,
            updated_data_template=data_template,
            existing_data_template=existing,
        )

        if len(new_data_columns) > 0:
            self.session.put(
                f"{self.base_path}/{existing.id}/datacolumns",
                json={
                    "DataColumns": [
                        x.model_dump(mode="json", by_alias=True, exclude_none=True)
                        for x in new_data_columns
                    ],
                },
            )
        data_column_enum_sequences = {}
        if len(data_column_enum_patches) > 0:
            for sequence, enum_patches in data_column_enum_patches.items():
                if len(enum_patches) == 0:
                    continue
                enums = self.session.put(
                    f"{self.base_path}/{existing.id}/datacolumns/{sequence}/enums",
                    json=enum_patches,  # these are simple dicts for now
                )
                data_column_enum_sequences[sequence] = [
                    EnumValidationValue(**x) for x in enums.json()
                ]
        if len(new_parameters) > 0:
            # remove enum types, will become enums after enum adds
            initial_enum_values = {}  # track original enum values by index
            no_enum_params = []
            for i, p in enumerate(new_parameters):
                if (
                    p.validation
                    and len(p.validation) > 0
                    and p.validation[0].datatype == DataType.ENUM
                ):
                    initial_enum_values[i] = p.validation[0].value
                    p.validation[0].datatype = DataType.STRING
                    p.validation[0].value = None
                no_enum_params.append(p)

            response = self.session.put(
                f"{self.base_path}/{existing.id}/parameters",
                json={
                    "Parameters": [
                        x.model_dump(mode="json", by_alias=True, exclude_none=True)
                        for x in no_enum_params
                    ],
                },
            )

            # Get returned parameters with sequences and restore enum values
            returned_parameters = [ParameterValue(**x) for x in response.json()["Parameters"]]
            for i, param in enumerate(returned_parameters):
                if i in initial_enum_values:
                    param.validation[0].value = initial_enum_values[i]
                    param.validation[0].datatype = DataType.ENUM  # Add this line

            # Add enum values to newly created parameters
            self._add_param_enums(
                data_template_id=existing.id,
                new_parameters=returned_parameters,
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

        if len(general_patches.data) > 0:
            payload = GeneralPatchPayload(data=general_patches.data)
            self.session.patch(
                path,
                json=payload.model_dump(mode="json", by_alias=True, exclude_none=True),
            )
        return self.get_by_id(id=data_template.id)

    @validate_call
    def delete(self, *, id: DataTemplateId) -> None:
        """Deletes a data template by its ID.

        Parameters
        ----------
        id : str
            The ID of the data template to delete.
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
        """
        Retrieve fully hydrated DataTemplate entities with optional filters.

        This method returns complete entity data using `get_by_ids`.
        Use `search()` for faster retrieval when you only need lightweight, partial (unhydrated) entities.

        Parameters
        ----------
        name : str, optional
            The name of the data template to filter by.
        user_id : str, optional
            The user ID to filter by.
        order_by : OrderBy, optional
            The order in which to sort results. Default is DESCENDING.
        max_items : int, optional
            Maximum number of items to return in total. If None, fetches all available items.
        offset : int, optional
            The result offset to begin pagination from.

        Returns
        -------
        Iterator[DataTemplate]
            An iterator over fully hydrated DataTemplate entities.
        """

        def batched(iterable, size: int):
            """Yield lists of up to `size` IDs from an iterable of entities with an `id` attribute."""
            it = (item.id for item in iterable)
            while batch := list(islice(it, size)):
                yield batch

        id_batches = batched(
            self.search(
                name=name,
                user_id=user_id,
                order_by=order_by,
                max_items=max_items,
                offset=offset,
            ),
            100,
        )

        for batch in id_batches:
            try:
                hydrated_templates = self.get_by_ids(ids=batch)
                yield from hydrated_templates
            except AlbertHTTPError as e:
                logger.warning(f"Error hydrating batch {batch}: {e}")
