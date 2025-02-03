from albert import Albert
from albert.resources.property_data import (
    InventoryDataColumn,
    InventoryPropertyDataCreate,
    TaskDataColumn,
    TaskPropertyCreate,
    TaskPropertyData,
)
from albert.resources.tasks import BaseTask, PropertyTask


def _get_latest_row(task_properties: TaskPropertyData) -> int:
    first_blk_interval = task_properties.data[0]
    trial_numbers = [
        int(x.trial_number)
        for x in first_blk_interval.trials
        if x.data_columns[0].property_data is not None
    ]
    return (
        0 if trial_numbers == [] else max([int(x.trial_number) for x in first_blk_interval.trials])
    )


def test_add_to_task(client: Albert, seeded_tasks: list[BaseTask]):
    prop_task = [x for x in seeded_tasks if isinstance(x, PropertyTask)][0]

    full_data = client.property_data.get_all_task_properties(task_id=prop_task.id)
    payload = []
    inital_count = _get_latest_row(full_data[0])
    for col in full_data[0].data[0].trials[0].data_columns:
        data_to_add = TaskPropertyCreate(
            interval_combination="default",
            data_column=TaskDataColumn(
                data_column_id=col.id,
                column_sequence=col.sequence,
            ),
            value="33.3",
            data_template=full_data[0].data_template,
        )
        payload.append(data_to_add)
    r = client.property_data.add_properties_to_task(
        task_id=prop_task.id,
        properties=payload,
        inventory_id=full_data[0].inventory.inventory_id,
        lot_id=full_data[0].inventory.lot_id,
        block_id=full_data[0].block_id,
    )
    final_count = _get_latest_row(r[0])
    assert final_count == inital_count + 1  # assert this added a new row
    assert isinstance(r[0], TaskPropertyData)


def test_add_to_inv(client: Albert, seeded_inventory, seeded_data_columns):
    data_columns = [
        InventoryDataColumn(
            data_column_id=seeded_data_columns[0].id,
            value="55.5",
        )
    ]
    r = client.property_data.add_properties_to_inventory(
        inventory_id=seeded_inventory[2].id, properties=data_columns
    )
    assert isinstance(r[0], InventoryPropertyDataCreate)
    assert r[0].inventory_id == seeded_inventory[2].id
    assert r[0].data_columns[0].data_column_id == seeded_data_columns[0].id
    assert r[0].data_columns[0].value == "55.5"


def test_search_property_data(client: Albert, seed_prefix: str, seeded_tasks: list[BaseTask]):
    # add some properties to the tasks
    pvalues = [22.4, 55.6, 52.4]
    property_search_string = f"{seed_prefix} - only unit 1"
    for i in range(len(seeded_tasks)):
        task = seeded_tasks[i]
        if not isinstance(task, PropertyTask):
            continue
        # the data template object on the task does not contain the data column values so we need
        # fetch them from the data template collection
        data_template = client.data_templates.get_by_id(id=task.blocks[0].data_template[0].id)
        workflow = client.workflows.get_by_id(id=task.blocks[0].workflow[0].id)
        interval_id = (
            workflow.interval_combinations[0].interval_id
            if workflow.interval_combinations
            else "default"
        )
        #  z = workflow.parameter_group_setpoints
        client.property_data.add_properties_to_task(
            task_id=task.id,
            inventory_id=task.inventory_information[0].inventory_id,
            block_id=task.blocks[0].id,
            properties=[
                TaskPropertyCreate(
                    data_template=data_template,
                    data_column=TaskDataColumn(
                        data_column_id=data_template.data_column_values[0].data_column_id,
                        column_sequence=data_template.data_column_values[0].column_sequence,
                    ),
                    value=str(pvalues.pop()),
                    interval_combination=interval_id,
                )
            ],
        )

    # now search for the properties
    _ = client.property_data.search(result=f"{property_search_string}(50-56)")
    # Currently the search indexes are not updated automatically so we cannot use
    # the SDK entities to search against and no other entities are static enough
    # for us to use as a reliable unit test.
    # For now we simply confirm that the above doesn't throw an HTTP exception (e.g. the search
    # syntax is valid and the call isn't returning a 400/500). Once the search index
    # moves to a more real-time dynamic update we can complete this test.
