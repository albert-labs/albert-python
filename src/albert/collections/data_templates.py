from collections.abc import Iterator
from itertools import islice

from pydantic import Field, validate_call

from albert.collections.base import BaseCollection
from albert.core.logging import logger
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import DataTemplateId, UserId
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
from albert.utils._patch import generate_data_template_patches


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

    def _add_param_enums(
        self,
        *,
        data_template_id: DataTemplateId,
        new_parameters: list[ParameterValue],
    ) -> list[EnumValidationValue]:
        """Adds enum values to a parameter."""

        data_template = self.get_by_id(id=data_template_id)
        existing_parameters = data_template.parameter_values

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
                    return [EnumValidationValue(**x) for x in enum_response.json()]

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
        initial_enum_values = {}  # use index to track the enum values
        cleaned_params = []
        if parameters is None or len(parameters) == 0:
            return self.get_by_id(id=data_template_id)
        for i, param in enumerate(parameters):
            if (
                param.validation
                and len(param.validation) > 0
                and param.validation[0].datatype == DataType.ENUM
            ):
                initial_enum_values[i] = param.validation[0].value
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
        for i, param in enumerate(returned_parameters):
            if i in initial_enum_values:
                param.validation[0].value = initial_enum_values[i]
                param.validation[0].datatype = DataType.ENUM
        self._add_param_enums(
            data_template_id=data_template_id,
            new_parameters=returned_parameters,
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
                logger.info(
                    f"SENDING DATA COLUMN ENUM PATCHES FOR SEQUENCE {sequence}: {enum_patches}"
                )
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
                    param.validation[0].datatype = DataType.ENUM

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

        if len(parameter_patches) > 0:
            patches_by_sequence = {}
            for p in parameter_patches:
                if p.rowId not in patches_by_sequence:
                    patches_by_sequence[p.rowId] = []
                patches_by_sequence[p.rowId].append(p)

            for sequence, patches in patches_by_sequence.items():
                # Filter out validation patches for sequences that have enum sequences
                if sequence in enum_sequences:
                    patches = [p for p in patches if p.attribute != "validation"]

                    enums = enum_sequences[sequence]
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
                    patches.append(enum_patch)

                payload = PGPatchPayload(data=patches)
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
