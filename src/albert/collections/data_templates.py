from collections.abc import Iterator

from pydantic import Field

from albert.collections.base import BaseCollection, OrderBy
from albert.exceptions import AlbertHTTPError
from albert.resources.data_templates import DataColumnValue, DataTemplate, ParameterValue
from albert.resources.identifiers import DataTemplateId
from albert.resources.parameter_groups import DataType, EnumValidationValue
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode
from albert.utils.patch_types import GeneralPatchDatum, GeneralPatchPayload, PGPatchPayload
from albert.utils.patches import (
    generate_data_template_patches,
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
        if data_template.parameter_values is None or len(data_template.parameter_values) == 0:
            return dt
        else:
            return self.add_parameters(
                data_template_id=dt.id, parameters=data_template.parameter_values
            )

    def _add_param_enums(
        self,
        *,
        data_template_id: DataTemplateId,
        new_parameters: list[ParameterValue],
    ):
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
                    self.session.put(
                        f"{self.base_path}/{data_template_id}/parameters/{this_sequence}/enums",
                        json=enum_patches,
                    )

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
        hits = list(self.list(name=name))
        for h in hits:
            if h.name.lower() == name.lower():
                return h
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
            The list of DataColumnValue objects to add to the data template.

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
            The list of ParameterValue objects to add to the data template.

        Returns
        -------
        DataTemplate
            The updated DataTemplate object.
        """
        # make sure the parameter values have a default validaion of string type.
        initial_enum_values = {}  # use index to track the enum values
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

        payload = {
            "Parameters": [
                x.model_dump(mode="json", by_alias=True, exclude_none=True) for x in parameters
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
        dt_with_params = self.get_by_id(id=data_template_id)
        for i, param in enumerate(dt_with_params.parameter_values):
            if i in initial_enum_values:
                param.validation[0].value = initial_enum_values[i]
                param.validation[0].datatype = DataType.ENUM

        return self.update(data_template=dt_with_params)

    def list(
        self,
        *,
        name: str | None = None,
        user_id: str | None = None,
        order_by: OrderBy = OrderBy.DESCENDING,
        limit: int = 100,
        offset: int = 0,
    ) -> Iterator[DataTemplate]:
        """
        Lists data template entities with optional filters.

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
        Iterator[DataTemplate]
            An iterator of DataTemplate objects matching the provided criteria.
        """

        def deserialize(items: list[dict]) -> Iterator[DataTemplate]:
            for item in items:
                id = item["albertId"]
                try:
                    yield self.get_by_id(id=id)
                except AlbertHTTPError as e:
                    logger.warning(f"Error fetching parameter group {id}: {e}")
            # get by ids is not currently returning metadata correctly, so temp fixing this
            # return self.get_by_ids(ids=[x["albertId"] for x in items])

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
            deserialize=deserialize,
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
        if len(data_column_enum_patches) > 0:
            for sequence, enum_patches in data_column_enum_patches.items():
                if len(enum_patches) == 0:
                    continue
                self.session.put(
                    f"{self.base_path}/{existing.id}/datacolumns/{sequence}/enums",
                    json=enum_patches,  # these are simple dicts for now
                )
        if len(new_parameters) > 0:
            self.session.put(
                f"{self.base_path}/{existing.id}/parameters",
                json={
                    "Parameters": [
                        x.model_dump(mode="json", by_alias=True, exclude_none=True)
                        for x in new_parameters
                    ],
                },
            )
        if len(parameter_enum_patches) > 0:
            for sequence, enum_patches in parameter_enum_patches.items():
                if len(enum_patches) == 0:
                    continue
                self.session.put(
                    f"{self.base_path}/{existing.id}/parameters/{sequence}/enums",
                    json=enum_patches,  # these are simple dicts for now
                )
        if len(parameter_patches) > 0:
            payload = PGPatchPayload(data=parameter_patches)
            self.session.patch(
                path + "/parameters",
                json=payload.model_dump(mode="json", by_alias=True, exclude_none=True),
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
