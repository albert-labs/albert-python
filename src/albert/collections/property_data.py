import re
from collections.abc import Iterator
from contextlib import suppress

import pandas as pd
from pydantic import validate_call

from albert.collections.base import BaseCollection, OrderBy
from albert.collections.tasks import TaskCollection
from albert.exceptions import NotFoundError
from albert.resources.base import EntityLink
from albert.resources.identifiers import (
    BlockId,
    DataColumnId,
    DataTemplateId,
    IntervalId,
    InventoryId,
    LotId,
    SearchInventoryId,
    SearchProjectId,
    TaskId,
    UserId,
)
from albert.resources.property_data import (
    BulkPropertyData,
    CheckPropertyData,
    DataEntity,
    InventoryDataColumn,
    InventoryPropertyData,
    InventoryPropertyDataCreate,
    PropertyDataPatchDatum,
    PropertyDataSearchItem,
    PropertyValue,
    TaskDataColumn,
    TaskPropertyCreate,
    TaskPropertyData,
    Trial,
)
from albert.resources.tasks import PropertyTask
from albert.session import AlbertSession
from albert.utils.logging import logger
from albert.utils.pagination import AlbertPaginator, PaginationMode
from albert.utils.patch_types import PatchOperation


class PropertyDataCollection(BaseCollection):
    """PropertyDataCollection is a collection class for managing Property Data entities in the Albert platform."""

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
        """Returns all the properties of an inventory item.

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the inventory item to retrieve properties for.

        Returns
        -------
        InventoryPropertyData
            The properties of the inventory item.
        """
        params = {"entity": "inventory", "id": [inventory_id]}
        response = self.session.get(url=self.base_path, params=params)
        response_json = response.json()
        return InventoryPropertyData(**response_json[0])

    @validate_call
    def add_properties_to_inventory(
        self, *, inventory_id: InventoryId, properties: list[InventoryDataColumn]
    ) -> list[InventoryPropertyDataCreate]:
        """Add new properties to an inventory item.

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the inventory item to add properties to.
        properties : list[InventoryDataColumn]
            The properties to add.

        Returns
        -------
        list[InventoryPropertyDataCreate]
            The registered properties.
        """
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
        """Update a property on an inventory item.

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the inventory item to update the property on.
        property_data : InventoryDataColumn
            The updated property data.

        Returns
        -------
        InventoryPropertyData
            The updated property data as returned by the server.
        """
        existing_properties = self.get_properties_on_inventory(inventory_id=inventory_id)
        existing_value = None
        for p in existing_properties.custom_property_data:
            if p.data_column.data_column_id == property_data.data_column_id:
                existing_value = (
                    p.data_column.property_data.value
                    if p.data_column.property_data.value is not None
                    else p.data_column.property_data.string_value
                    if p.data_column.property_data.string_value is not None
                    else str(p.data_column.property_data.numeric_value)
                    if p.data_column.property_data.numeric_value is not None
                    else None
                )
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
        """Returns all the properties within a Property Task block for a specific inventory item.

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the inventory.
        task_id : TaskId
            The Property task ID.
        block_id : BlockId
            The Block ID of the block to retrieve properties for.
        lot_id : LotId | None, optional
            The specific Lot of the inventory Item to retrieve lots for, by default None

        Returns
        -------
        TaskPropertyData
            The properties of the inventory item within the block.
        """
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
        """Checks if a task has data.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task to check for data.

        Returns
        -------
        list[CheckPropertyData]
            A list of CheckPropertyData objects representing the data status of each block + inventory item of the task.
        """
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
        """Check if a specific block interval has data.

        Parameters
        ----------
        block_id : BlockId
            The ID of the block.
        task_id : TaskId
            The ID of the task.
        interval_id : IntervalId
            The ID of the interval.

        Returns
        -------
        CheckPropertyData
            _description_
        """
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
        """Returns all the properties for a specific task.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task to retrieve properties for.

        Returns
        -------
        list[TaskPropertyData]
            A list of TaskPropertyData objects representing the properties within the task.
        """
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
    ) -> list[TaskPropertyData]:
        """Updates a specific property on a task.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task.
        patch_payload : list[PropertyDataPatchDatum]
            The specific patch to make to update the property.

        Returns
        -------
        list[TaskPropertyData]
            A list of TaskPropertyData objects representing the properties within the task.
        """
        if len(patch_payload) > 0:
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
        """
        Add new task properties for a given task.

        This method only works for new values. If a trial number is provided in the TaskPropertyCreate,
        it must relate to an existing trial. New trials must be added with no trial number provided.
        Do not try to create multiple new trials in one call as this will lead to unexpected behavior.
        Build out new trials in a loop if many new trials are needed.

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the inventory.
        task_id : TaskId
            The ID of the task.
        block_id : BlockId
            The ID of the block.
        lot_id : LotId, optional
            The ID of the lot, by default None.
        properties : list[TaskPropertyCreate]
            A list of TaskPropertyCreate objects representing the properties to add.

        Returns
        -------
        list[TaskPropertyData]
            The newly created task properties.
        """
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

    @validate_call
    def update_or_create_task_properties(
        self,
        *,
        inventory_id: InventoryId,
        task_id: TaskId,
        block_id: BlockId,
        lot_id: LotId | None = None,
        properties: list[TaskPropertyCreate],
    ) -> list[TaskPropertyData]:
        """
        Update or create task properties for a given task.

        If a trial number is provided in the TaskPropertyCreate, it must relate to an existing trial.
        New trials must be added with no trial number provided. Do not try to create multiple new trials
        in one call as this will lead to unexpected behavior. Build out new trials in a loop if many new
        trials are needed.

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the inventory.
        task_id : TaskId
            The ID of the task.
        block_id : BlockId
            The ID of the block.
        lot_id : LotId, optional
            The ID of the lot, by default None.
        properties : list[TaskPropertyCreate]
            A list of TaskPropertyCreate objects representing the properties to update or create.

        Returns
        -------
        list[TaskPropertyData]
            The updated or newly created task properties.

        """
        existing_data_rows = self.get_task_block_properties(
            inventory_id=inventory_id, task_id=task_id, block_id=block_id, lot_id=lot_id
        )
        update_patches, new_values = self._form_existing_row_value_patches(
            existing_data_rows=existing_data_rows, properties=properties
        )

        calculated_patches = self._form_calculated_task_property_patches(
            existing_data_rows=existing_data_rows, properties=properties
        )
        all_patches = update_patches + calculated_patches
        if len(new_values) > 0:
            self.update_property_on_task(task_id=task_id, patch_payload=all_patches)
            return self.add_properties_to_task(
                inventory_id=inventory_id,
                task_id=task_id,
                block_id=block_id,
                lot_id=lot_id,
                properties=new_values,
            )
        else:
            return self.update_property_on_task(task_id=task_id, patch_payload=all_patches)

    def bulk_load_task_properties(
        self,
        *,
        inventory_id: InventoryId,
        task_id: TaskId,
        block_id: BlockId,
        property_data: BulkPropertyData,
        interval="default",
        lot_id: LotId = None,
    ) -> list[TaskPropertyData]:
        """
        Bulk load task properties for a given task. WARNING: This will overwrite any existing properties!
        BulkPropertyData column names must exactly match the names of the data columns (Case Sensitive).

        Parameters
        ----------
        inventory_id : InventoryId
            The ID of the inventory.
        task_id : TaskId
            The ID of the task.
        block_id : BlockId
            The ID of the block.
        lot_id : LotId, optional
            The ID of the lot, by default None.
        interval : str, optional
            The interval to use for the properties, by default "default". Can be obtained using Workflow.get_interval_id().
        property_data : BulkPropertyData
            A list of columnwise data containing all your rows of data for a single interval. Can be created using BulkPropertyData.from_dataframe().

        Returns
        -------
        list[TaskPropertyData]
            The updated or newly created task properties.

        Example
        -------

        ```python
        from albert.resources.property_data import BulkPropertyData

        data = BulkPropertyData.from_dataframe(df=my_dataframe)
        res = client.property_data.bulk_load_task_properties(
            block_id="BLK1",
            inventory_id="INVEXP102748-042",
            property_data=data,
            task_id="TASFOR291760",
        )

        [TaskPropertyData(id="TASFOR291760", ...)]
        ```
        """
        property_df = pd.DataFrame(
            {x.data_column_name: x.data_series for x in property_data.columns}
        )

        def _get_column_map(dataframe: pd.DataFrame, property_data: TaskPropertyData):
            data_col_info = property_data.data[0].trials[0].data_columns  # PropertyValue
            column_map = {}
            for col in dataframe.columns:
                column = [x for x in data_col_info if x.name == col]
                if len(column) == 1:
                    column_map[col] = column[0]
                else:
                    raise ValueError(
                        f"Column '{col}' not found in block data columns or multiple matches found."
                    )
            return column_map

        def _df_to_task_prop_create_list(
            dataframe: pd.DataFrame,
            column_map: dict[str, PropertyValue],
            data_template_id: DataTemplateId,
        ) -> list[TaskPropertyCreate]:
            task_prop_create_list = []
            for i, row in dataframe.iterrows():
                for col_name, col_info in column_map.items():
                    if col_name not in dataframe.columns:
                        raise ValueError(f"Column '{col_name}' not found in DataFrame.")

                    task_prop_create = TaskPropertyCreate(
                        data_column=TaskDataColumn(
                            data_column_id=col_info.id,
                            column_sequence=col_info.sequence,
                        ),
                        value=str(row[col_name]),
                        visible_trial_number=i + 1,
                        interval_combination=interval,
                        data_template=EntityLink(id=data_template_id),
                    )
                    task_prop_create_list.append(task_prop_create)
            return task_prop_create_list

        task_prop_data = self.get_task_block_properties(
            inventory_id=inventory_id, task_id=task_id, block_id=block_id, lot_id=lot_id
        )
        column_map = _get_column_map(property_df, task_prop_data)
        all_task_prop_create = _df_to_task_prop_create_list(
            dataframe=property_df,
            column_map=column_map,
            data_template_id=task_prop_data.data_template.id,
        )
        with suppress(NotFoundError):
            # This is expected if the task is new and has no data yet.
            self.bulk_delete_task_data(
                task_id=task_id,
                block_id=block_id,
                inventory_id=inventory_id,
                lot_id=lot_id,
                interval_id=interval,
            )
        return self.add_properties_to_task(
            inventory_id=inventory_id,
            task_id=task_id,
            block_id=block_id,
            lot_id=lot_id,
            properties=all_task_prop_create,
        )

    def bulk_delete_task_data(
        self,
        *,
        task_id: TaskId,
        block_id: BlockId,
        inventory_id: InventoryId,
        lot_id: LotId | None = None,
        interval_id=None,
    ) -> None:
        """
        Bulk delete task data for a given task.

        Parameters
        ----------
        task_id : TaskId
            The ID of the task.
        block_id : BlockId
            The ID of the block.
        inventory_id : InventoryId
            The ID of the inventory.
        lot_id : LotId, optional
            The ID of the lot, by default None.
        interval_id : IntervalId, optional
            The ID of the interval, by default None. If provided, will delete data for this specific interval.

        Returns
        -------
        None
        """
        params = {
            "inventoryId": inventory_id,
            "blockId": block_id,
            "lotId": lot_id,
            "intervalRow": interval_id if interval_id != "default" else None,
        }
        params = {k: v for k, v in params.items() if v is not None}
        self.session.delete(f"{self.base_path}/{task_id}", params=params)

    ################### Methods to support Updated Row Value patches #################

    def _form_existing_row_value_patches(
        self, *, existing_data_rows: TaskPropertyData, properties: list[TaskPropertyCreate]
    ):
        patches = []
        new_properties = []

        for prop in properties:
            if prop.trial_number is None:
                new_properties.append(prop)
                continue

            prop_patches = self._process_property(prop, existing_data_rows)
            if prop_patches:
                patches.extend(prop_patches)
            else:
                new_properties.append(prop)
        return patches, new_properties

    def _process_property(
        self, prop: TaskPropertyCreate, existing_data_rows: TaskPropertyData
    ) -> list | None:
        for interval in existing_data_rows.data:
            if interval.interval_combination != prop.interval_combination:
                continue

            for trial in interval.trials:
                if trial.trial_number != prop.trial_number:
                    continue

                trial_patches = self._process_trial(trial, prop)
                if trial_patches:
                    return trial_patches

        return None

    def _process_trial(self, trial: Trial, prop: TaskPropertyCreate) -> list | None:
        for data_column in trial.data_columns:
            if (
                data_column.data_column_unique_id
                == f"{prop.data_column.data_column_id}#{prop.data_column.column_sequence}"
                and data_column.property_data is not None
            ):
                if data_column.property_data.value == prop.value:
                    # No need to update this value
                    return None
                return [
                    PropertyDataPatchDatum(
                        id=data_column.property_data.id,
                        operation=PatchOperation.UPDATE,
                        attribute="value",
                        new_value=prop.value,
                        old_value=data_column.property_data.value,
                    )
                ]

        return None

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
            if on_platform_row is not None:
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
                calculation = calculation.replace(
                    "^", "**"
                )  # Replace '^' with '**' for exponentiation
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
                    elif str(column.property_data.value) != str(
                        recalculated_value
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
        data_template_ids: DataTemplateId | list[DataTemplateId] | None = None,
        data_column_ids: DataColumnId | list[DataColumnId] | None = None,
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
        data_template_ids : DataTemplateId or list of DataTemplateId, optional
            Filter by data template IDs.
        data_column_ids: DataColumnId or list of DataColumnId, optional
            Filter by data column IDs.
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
        if isinstance(data_template_ids, str):
            data_template_ids = [data_template_ids]
        if isinstance(data_column_ids, str):
            data_column_ids = [data_column_ids]
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
            "inventoryIds": inventory_ids if inventory_ids is not None else None,
            "projectIds": project_ids if project_ids is not None else None,
            "lotIds": lot_ids if lot_ids is not None else None,
            "dataTemplateId": data_template_ids if data_template_ids is not None else None,
            "dataColumnId": data_column_ids if data_column_ids is not None else None,
            "category": [c.value for c in category] if category is not None else None,
            "dataTemplates": data_templates,
            "dataColumns": data_columns,
            "parameters": parameters,
            "parameterGroup": parameter_group,
            "unit": unit,
            "createdBy": created_by if created_by is not None else None,
            "taskCreatedBy": task_created_by if task_created_by is not None else None,
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
