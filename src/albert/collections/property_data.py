import re
from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection, OrderBy
from albert.collections.tasks import TaskCollection
from albert.resources.identifiers import (
    BlockId,
    IntervalId,
    InventoryId,
    LotId,
    SearchInventoryId,
    SearchProjectId,
    TaskId,
    UserId,
)
from albert.resources.property_data import (
    CheckPropertyData,
    DataEntity,
    InventoryDataColumn,
    InventoryPropertyData,
    InventoryPropertyDataCreate,
    PropertyDataPatchDatum,
    PropertyDataSearchItem,
    PropertyValue,
    TaskPropertyCreate,
    TaskPropertyData,
    Trial,
)
from albert.resources.tasks import PropertyTask
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode
from albert.utils.patches import PatchOperation


class PropertyDataCollection(BaseCollection):
    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initializes the CompanyCollection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{PropertyDataCollection._api_version}/propertydata"

    @validate_call
    def _get_task_from_id(self, *, id: TaskId) -> PropertyTask:
        return TaskCollection(session=self.session).get_by_id(id=id)

    @validate_call
    def get_properties_on_inventory(self, *, inventory_id: InventoryId) -> InventoryPropertyData:
        """Returns all the properties of an inventory item."""
        params = {"entity": "inventory", "id": [inventory_id]}
        response = self.session.get(url=self.base_path, params=params)
        response_json = response.json()
        return InventoryPropertyData(**response_json[0])

    @validate_call
    def add_properties_to_inventory(
        self, *, inventory_id: InventoryId, properties: list[InventoryDataColumn]
    ) -> list[InventoryPropertyDataCreate]:
        returned = []
        for p in properties:
            # Can only add one at a time.
            create_object = InventoryPropertyDataCreate(
                inventory_id=inventory_id, data_columns=[p]
            )
            response = self.session.post(
                self.base_path,
                json=create_object.model_dump(exclude_none=True, by_alias=True, mode="json"),
            )
            response_json = response.json()
            logger.info(response_json.get("message", None))
            returned.append(InventoryPropertyDataCreate(**response_json))
        return returned

    @validate_call
    def update_property_on_inventory(
        self, *, inventory_id: InventoryId, property_data: InventoryDataColumn
    ) -> InventoryPropertyData:
        existing_properties = self.get_properties_on_inventory(inventory_id=inventory_id)
        existing_value = None
        for p in existing_properties.custom_property_data:
            if p.data_column.data_column_id == property_data.data_column_id:
                existing_value = p.data_column.property_data.value
                existing_id = p.data_column.property_data.id
                break
        if existing_value is not None:
            payload = [
                PropertyDataPatchDatum(
                    operation=PatchOperation.UPDATE,
                    id=existing_id,
                    attribute="value",
                    new_value=property_data.value,
                    old_value=existing_value,
                )
            ]
        else:
            payload = [
                PropertyDataPatchDatum(
                    operation=PatchOperation.ADD,
                    id=existing_id,
                    attribute="value",
                    new_value=property_data.value,
                )
            ]

        self.session.patch(
            url=f"{self.base_path}/{inventory_id}",
            json=[x.model_dump(exclude_none=True, by_alias=True, mode="json") for x in payload],
        )
        return self.get_properties_on_inventory(inventory_id=inventory_id)

    @validate_call
    def get_task_block_properties(
        self,
        *,
        inventory_id: InventoryId,
        task_id: TaskId,
        block_id: BlockId,
        lot_id: LotId | None = None,
    ) -> TaskPropertyData:
        params = {
            "entity": "task",
            "blockId": block_id,
            "id": task_id,
            "inventoryId": inventory_id,
            "lotId": lot_id,
        }
        params = {k: v for k, v in params.items() if v is not None}

        response = self.session.get(url=self.base_path, params=params)
        response_json = response.json()
        return TaskPropertyData(**response_json[0])

    @validate_call
    def check_for_task_data(self, *, task_id: TaskId) -> list[CheckPropertyData]:
        task_info = self._get_task_from_id(id=task_id)

        params = {
            "entity": "block",
            "action": "checkdata",
            "parentId": task_id,
            "id": [x.id for x in task_info.blocks],
        }

        response = self.session.get(url=self.base_path, params=params)
        return [CheckPropertyData(**x) for x in response.json()]

    @validate_call
    def check_block_interval_for_data(
        self, *, block_id: BlockId, task_id: TaskId, interval_id: IntervalId
    ) -> CheckPropertyData:
        params = {
            "entity": "block",
            "action": "checkdata",
            "id": block_id,
            "parentId": task_id,
            "intervalId": interval_id,
        }

        response = self.session.get(url=self.base_path, params=params)
        return CheckPropertyData(response.json())

    @validate_call
    def get_all_task_properties(self, *, task_id: TaskId) -> list[TaskPropertyData]:
        all_info = []
        task_data_info = self.check_for_task_data(task_id=task_id)
        for combo_info in task_data_info:
            all_info.append(
                self.get_task_block_properties(
                    inventory_id=combo_info.inventory_id,
                    task_id=task_id,
                    block_id=combo_info.block_id,
                    lot_id=combo_info.lot_id,
                )
            )

        return all_info

    @validate_call
    def update_property_on_task(
        self, *, task_id: TaskId, patch_payload: list[PropertyDataPatchDatum]
    ):
        if len(patch_payload) >= 0:
            self.session.patch(
                url=f"{self.base_path}/{task_id}",
                json=[
                    x.model_dump(exclude_none=True, by_alias=True, mode="json")
                    for x in patch_payload
                ],
            )
        return self.get_all_task_properties(task_id=task_id)

    @validate_call
    def add_properties_to_task(
        self,
        *,
        inventory_id: InventoryId,
        task_id: TaskId,
        block_id: BlockId,
        lot_id: LotId | None = None,
        properties: list[TaskPropertyCreate],
    ):
        params = {
            "blockId": block_id,
            "inventoryId": inventory_id,
            "lotId": lot_id,
            "autoCalculate": "true",
            "history": "true",
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = self.session.post(
            url=f"{self.base_path}/{task_id}",
            json=[x.model_dump(exclude_none=True, by_alias=True, mode="json") for x in properties],
            params=params,
        )

        registered_properties = [
            TaskPropertyCreate(**x) for x in response.json() if "DataTemplate" in x
        ]
        existing_data_rows = self.get_task_block_properties(
            inventory_id=inventory_id, task_id=task_id, block_id=block_id, lot_id=lot_id
        )
        patches = self._form_calculated_task_property_patches(
            existing_data_rows=existing_data_rows, properties=registered_properties
        )
        if len(patches) > 0:
            return self.update_property_on_task(task_id=task_id, patch_payload=patches)
        else:
            return self.get_all_task_properties(task_id=task_id)

    ################### Methods to support calculated value patches ##################

    def _form_calculated_task_property_patches(
        self, *, existing_data_rows: TaskPropertyData, properties: list[TaskPropertyCreate]
    ):
        patches = []
        covered_interval_trials = set()
        first_row_data_column = existing_data_rows.data[0].trials[0].data_columns
        columns_used_in_calculations = self._get_all_columns_used_in_calculations(
            first_row_data_column=first_row_data_column
        )
        for posted_prop in properties:
            this_interval_trial = f"{posted_prop.interval_combination}-{posted_prop.trial_number}"
            if (
                this_interval_trial in covered_interval_trials
                or posted_prop.data_column.column_sequence not in columns_used_in_calculations
            ):
                continue  # we don't need to worry about it hence we skip
            on_platform_row = self._get_on_platform_row(
                existing_data_rows=existing_data_rows,
                trial_number=posted_prop.trial_number,
                interval_combination=posted_prop.interval_combination,
            )

            these_patches = self._generate_data_patch_payload(trial=on_platform_row)
            patches.extend(these_patches)
            covered_interval_trials.add(this_interval_trial)
        return patches

    def _get_on_platform_row(
        self, *, existing_data_rows: TaskPropertyData, interval_combination: str, trial_number: int
    ):
        for interval in existing_data_rows.data:
            if interval.interval_combination == interval_combination:
                for trial in interval.trials:
                    if trial.trial_number == trial_number:
                        return trial
        return None

    def _get_columns_used_in_calculation(self, *, calculation: str | None, used_columns: set[str]):
        if calculation is None:
            return used_columns
        column_pattern = r"COL\d+"
        matches = re.findall(column_pattern, calculation)
        used_columns.update(set(matches))
        return used_columns

    def _get_all_columns_used_in_calculations(self, *, first_row_data_column: list[PropertyValue]):
        used_columns = set()
        for calc in [x.calculation for x in first_row_data_column]:
            used_columns = self._get_columns_used_in_calculation(
                calculation=calc, used_columns=used_columns
            )
        return used_columns

    def _evaluate_calculation(self, *, calculation: str, column_values: dict) -> float | None:
        calculation = calculation.lstrip("=")  # Remove '=' at the start of the calculation
        try:
            # Replace column names with their numeric values in the calculation string
            for col, value in column_values.items():
                calculation = calculation.replace(col, str(value))
            # Evaluate the resulting expression
            return eval(calculation)
        except Exception as e:
            logger.info(
                f"Error evaluating calculation '{calculation}': {e}. Likely do not have all values needed."
            )
            return None

    def _generate_data_patch_payload(self, *, trial: Trial) -> list[PropertyDataPatchDatum]:
        column_values = {
            col.sequence: col.property_data.value
            for col in trial.data_columns
            if col.property_data is not None
        }

        patch_data = []
        for column in trial.data_columns:
            if column.calculation:
                # Evaluate the recalculated value
                recalculated_value = self._evaluate_calculation(
                    calculation=column.calculation, column_values=column_values
                )
                if recalculated_value is not None:
                    # Determine whether this is an ADD or UPDATE operation
                    if column.property_data.value is None:  # No existing value
                        patch_data.append(
                            PropertyDataPatchDatum(
                                id=column.property_data.id,
                                operation=PatchOperation.ADD,
                                attribute="value",
                                new_value=recalculated_value,
                                old_value=None,
                            )
                        )
                    elif (
                        column.property_data.value != recalculated_value
                    ):  # Existing value differs
                        patch_data.append(
                            PropertyDataPatchDatum(
                                id=column.property_data.id,
                                operation=PatchOperation.UPDATE,
                                attribute="value",
                                new_value=recalculated_value,
                                old_value=column.property_data.value,
                            )
                        )

        return patch_data

    @validate_call
    def search(
        self,
        *,
        limit: int = 100,
        result: str | None = None,
        text: str | None = None,
        # Sorting/pagination
        order: OrderBy | None = None,
        sort_by: str | None = None,
        # Core platform identifiers
        inventory_ids: list[SearchInventoryId] | SearchInventoryId | None = None,
        project_ids: list[SearchProjectId] | SearchProjectId | None = None,
        lot_ids: list[LotId] | LotId | None = None,
        # Data structure filters
        category: list[DataEntity] | DataEntity | None = None,
        data_templates: list[str] | str | None = None,
        data_columns: list[str] | str | None = None,
        # Data content filters
        parameters: list[str] | str | None = None,
        parameter_group: list[str] | str | None = None,
        unit: list[str] | str | None = None,
        # User filters
        created_by: list[UserId] | UserId | None = None,
        task_created_by: list[UserId] | UserId | None = None,
        # Response customization
        return_fields: list[str] | str | None = None,
        return_facets: list[str] | str | None = None,
    ) -> Iterator[PropertyDataSearchItem]:
        """Search for property data with various filtering options.

        Parameters
        ----------
        limit : int, default=100
            Maximum number of results to return.
        result : str, optional
            Find results using search syntax. e.g. to find all results with viscosity < 200 at a temperature of 25 we would do
            result=viscosity(<200)@temperature(25)
        text : str, optional
            Free text search across all searchable fields.
        order : OrderBy, optional
            Sort order (ascending/descending).
        sort_by : str, optional
            Field to sort results by.
        inventory_ids : SearchInventoryIdType or list of SearchInventoryIdType, optional
            Filter by inventory IDs.
        project_ids : ProjectIdType or list of ProjectIdType, optional
            Filter by project IDs.
        lot_ids : LotIdType or list of LotIdType, optional
            Filter by lot IDs.
        category : DataEntity or list of DataEntity, optional
            Filter by data entity categories.
        data_templates : str or list of str (exact match), optional
            Filter by data template names.
        data_columns : str or list of str (exact match), optional
            Filter by data column names (currently non-functional).
        parameters : str or list of str (exact match), optional
            Filter by parameter names.
        parameter_group : str or list of str (exact match), optional
            Filter by parameter group names.
        unit : str or list of str (exact match), optional
            Filter by unit names.
        created_by : UserIdType or list of UserIdType, optional
            Filter by creator user IDs.
        task_created_by : UserIdType or list of UserIdType, optional
            Filter by task creator user IDs.
        return_fields : str or list of str, optional
            Specific fields to include in results. If None, returns all fields.
        return_facets : str or list of str, optional
            Specific facets to include in results.

        Returns
        -------
        dict
            Search results matching the specified criteria.
        """

        def deserialize(items: list[dict]) -> list[PropertyDataSearchItem]:
            return [PropertyDataSearchItem.model_validate(x) for x in items]

        if isinstance(inventory_ids, str):
            inventory_ids = [inventory_ids]
        if isinstance(project_ids, str):
            project_ids = [project_ids]
        if isinstance(lot_ids, str):
            lot_ids = [lot_ids]
        if isinstance(category, DataEntity):
            category = [category]
        if isinstance(data_templates, str):
            data_templates = [data_templates]
        if isinstance(data_columns, str):
            data_columns = [data_columns]
        if isinstance(parameters, str):
            parameters = [parameters]
        if isinstance(parameter_group, str):
            parameter_group = [parameter_group]
        if isinstance(unit, str):
            unit = [unit]
        if isinstance(created_by, str):
            created_by = [created_by]
        if isinstance(task_created_by, str):
            task_created_by = [task_created_by]
        if isinstance(return_fields, str):
            return_fields = [return_fields]
        if isinstance(return_facets, str):
            return_facets = [return_facets]

        params = {
            "limit": limit,
            "result": result,
            "text": text,
            "order": order.value if order is not None else None,
            "sortBy": sort_by,
            "inventoryIds": [str(x) for x in inventory_ids] if inventory_ids is not None else None,
            "projectIds": [str(x) for x in project_ids] if project_ids is not None else None,
            "lotIds": [str(x) for x in lot_ids] if lot_ids is not None else None,
            "category": [c.value for c in category] if category is not None else None,
            "dataTemplates": data_templates,
            "dataColumns": data_columns,
            "parameters": parameters,
            "parameterGroup": parameter_group,
            "unit": unit,
            "createdBy": [str(x) for x in created_by] if created_by is not None else None,
            "taskCreatedBy": [str(x) for x in task_created_by]
            if task_created_by is not None
            else None,
            "returnFields": return_fields,
            "returnFacets": return_facets,
        }

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            params=params,
            session=self.session,
            deserialize=deserialize,
        )
