import re

from albert.collections.base import BaseCollection
from albert.collections.tasks import TaskCollection
from albert.resources.property_data import (
    CheckPropertyData,
    InventoryDataColumn,
    InventoryPropertyData,
    InventoryPropertyDataCreate,
    PropertyDataPatchDatum,
    PropertyValue,
    TaskPropertyCreate,
    TaskPropertyData,
    Trial,
)
from albert.resources.tasks import PropertyTask
from albert.session import AlbertSession
from albert.utils.logging import logger
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

    def _get_task_from_id(self, *, id: str) -> PropertyTask:
        return TaskCollection(session=self.session).get_by_id(id=id)

    def get_properties_on_inventory(self, *, inventory_id: str) -> InventoryPropertyData:
        """Returns all the properties of an inventory item."""
        response = self.session.get(url=f"{self.base_path}?entity=inventory&id[]={inventory_id}")
        response_json = response.json()
        return InventoryPropertyData(**response_json[0])

    def add_properties_to_inventory(
        self, *, inventory_id: str, properties: list[InventoryDataColumn]
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

    def update_property_on_inventory(
        self, *, inventory_id: str, property_data: InventoryDataColumn
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

    def get_task_block_properties(
        self, *, inventory_id: str, task_id: str, block_id: str, lot_id: str | None = None
    ) -> TaskPropertyData:
        if not task_id.startswith("TAS"):
            task_id = f"TAS{task_id}"
        url = f"{self.base_path}?entity=task&blockId={block_id}&id={task_id}&inventoryId={inventory_id}"
        if lot_id is not None:
            url = f"{url}&lotId={lot_id}"

        response = self.session.get(url=url)
        response_json = response.json()
        return TaskPropertyData(**response_json[0])

    def check_for_task_data(self, *, task_id: str) -> list[CheckPropertyData]:
        if not task_id.startswith("TAS"):
            task_id = f"TAS{task_id}"
        task_info = self._get_task_from_id(id=task_id)

        blk_ids = [x.id for x in task_info.blocks]
        blk_query = "&".join([f"id={x}" for x in blk_ids])
        response = self.session.get(
            url=f"{self.base_path}?entity=block&action=checkdata&{blk_query}&parentId={task_id}"
        )
        return [CheckPropertyData(**x) for x in response.json()]

    def check_block_interval_for_data(
        self, *, block_id: str, task_id: str, interval_id: str
    ) -> CheckPropertyData:
        if not task_id.startswith("TAS"):
            task_id = f"TAS{task_id}"
        response = self.session.get(
            url=f"{self.base_path}?entity=block&action=checkdata&id={block_id}&parentId={task_id}&intervalId={interval_id}"
        )
        return CheckPropertyData(response.json())

    def get_all_task_properties(self, *, task_id: str) -> list[TaskPropertyData]:
        if not task_id.startswith("TAS"):
            task_id = f"TAS{task_id}"
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

    def update_property_on_task(
        self, *, task_id: str, patch_payload: list[PropertyDataPatchDatum]
    ):
        if len(patch_payload) >= 0:
            if not task_id.startswith("TAS"):
                task_id = f"TAS{task_id}"
            self.session.patch(
                url=f"{self.base_path}/{task_id}",
                json=[
                    x.model_dump(exclude_none=True, by_alias=True, mode="json")
                    for x in patch_payload
                ],
            )
        return self.get_all_task_properties(task_id=task_id)

    def add_properies_to_task(
        self,
        *,
        inventory_id: str,
        task_id: str,
        block_id: str,
        lot_id: str | None = None,
        properties: list[TaskPropertyCreate],
    ):
        if not task_id.startswith("TAS"):
            task_id = f"TAS{task_id}"
        if not inventory_id.startswith("INV"):
            inventory_id = f"INV{inventory_id}"
        url = f"{self.base_path}/{task_id}?blockId={block_id}&inventoryId={inventory_id}&autoCalculate=true&history=true"
        if lot_id is not None:
            url = f"{url}&lotId={lot_id}"

        response = self.session.post(
            url=url,
            json=[x.model_dump(exclude_none=True, by_alias=True, mode="json") for x in properties],
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

    def delete_task_property_row(
        self,
        *,
        task_id: str,
        inventory_id: str,
        block_id: str | None = None,
        lot_id: str | None = None,
        interval_row: str | None,
    ) -> None:
        if not task_id.startswith("TAS"):
            task_id = f"TAS{task_id}"
        if not inventory_id.startswith("INV"):
            inventory_id = f"INV{inventory_id}"
        url = f"{self.base_path}/{task_id}?blockId={block_id}&inventoryId={inventory_id}"
        if lot_id is not None:
            url = f"{url}&lotId={lot_id}"
        if interval_row is not None:
            url = f"{url}&intervalRow={interval_row}"
        self.session.delete(url=url)

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

    def _get_columns_used_in_calculation(self, *, calculation: str, used_columns: set[str]):
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
