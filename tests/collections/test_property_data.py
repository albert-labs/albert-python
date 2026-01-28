from contextlib import suppress

import pytest

from albert import Albert
from albert.exceptions import NotFoundError
from albert.resources.data_columns import DataColumn
from albert.resources.data_templates import DataColumnValue, DataTemplate
from albert.resources.property_data import (
    BulkPropertyData,
    BulkPropertyDataColumn,
    CheckPropertyData,
    InventoryDataColumn,
    InventoryPropertyData,
    InventoryPropertyDataCreate,
    TaskDataColumn,
    TaskPropertyCreate,
    TaskPropertyData,
)
from albert.resources.tasks import (
    BaseTask,
    Block,
    PropertyTask,
    TaskCategory,
    TaskInventoryInformation,
)


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


def test_add_properties_to_task(client: Albert, seeded_tasks: list[BaseTask]):
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
        return_scope="block",
    )
    final_count = _get_latest_row(r[0])
    assert final_count == inital_count + 1  # assert this added a new row
    assert isinstance(r[0], TaskPropertyData)


def test_check_for_interval_data(client: Albert, seeded_tasks, seeded_workflows):
    task = [x for x in seeded_tasks if isinstance(x, PropertyTask)][0]
    for block in task.blocks:
        this_workflow = [x for x in seeded_workflows if x.id in [y.id for y in block.workflow]][0]
        if this_workflow.interval_combinations and len(this_workflow.interval_combinations) > 0:
            for interval in this_workflow.interval_combinations:
                check = client.property_data.check_block_interval_for_data(
                    block_id=block.id, task_id=task.id, interval_id=interval.interval_id
                )

                assert isinstance(check, CheckPropertyData)


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
                        column_sequence=data_template.data_column_values[0].sequence,
                    ),
                    value=str(pvalues.pop()),
                    interval_combination=interval_id,
                )
            ],
            return_scope="none",
        )

    # now search for the properties
    _ = client.property_data.search(result=f"{property_search_string}(50-56)", max_items=5)
    # Currently the search indexes are not updated automatically so we cannot use
    # the SDK entities to search against and no other entities are static enough
    # for us to use as a reliable unit test.
    # For now we simply confirm that the above doesn't throw an HTTP exception (e.g. the search
    # syntax is valid and the call isn't returning a 400/500). Once the search index
    # moves to a more real-time dynamic update we can complete this test.


def test_get_properties_on_inventory(
    client: Albert,
    seeded_inventory: list[BaseTask],
):
    # get the properties on the inventory
    inv = seeded_inventory[0]
    r = client.property_data.get_properties_on_inventory(inventory_id=inv.id)
    assert isinstance(r, InventoryPropertyData)
    assert r.inventory_id == inv.id


def test_bulk_load_and_delete_properties_to_property_task(
    client: Albert, seeded_tasks: list[BaseTask]
):
    prop_task = [x for x in seeded_tasks if isinstance(x, PropertyTask)][0]
    data_template = client.data_templates.get_by_id(id=prop_task.blocks[0].data_template[0].id)
    workflow = client.workflows.get_by_id(id=prop_task.blocks[0].workflow[0].id)
    interval_id = (
        workflow.interval_combinations[0].interval_id
        if workflow.interval_combinations
        else "default"
    )
    #  z = workflow.parameter_group_setpoints
    data_cols_in_dt = [
        client.data_columns.get_by_id(id=x.data_column_id)
        for x in data_template.data_column_values
    ]
    dc_names = [x.name for x in data_cols_in_dt]
    faux_col_vals = {}
    for name in dc_names:
        faux_col_vals[name] = [f"{name} - {i}" for i in range(10)]

    new_data = BulkPropertyData(
        columns=[
            BulkPropertyDataColumn(data_column_name=name, data_series=vals)
            for name, vals in faux_col_vals.items()
        ]
    )
    r = client.property_data.bulk_load_task_properties(
        inventory_id=prop_task.inventory_information[0].inventory_id,
        block_id=prop_task.blocks[0].id,
        task_id=prop_task.id,
        property_data=new_data,
        interval=interval_id,
        lot_id=prop_task.inventory_information[0].lot_id,
        return_scope="block",
    )

    assert isinstance(r[0], TaskPropertyData)
    assert len(r) == 1
    assert len(r[0].data) == 1
    assert len(r[0].data[0].trials) == 10

    # now delete the properties
    client.property_data.bulk_delete_task_data(
        task_id=prop_task.id,
        block_id=prop_task.blocks[0].id,
        inventory_id=prop_task.inventory_information[0].inventory_id,
        lot_id=prop_task.inventory_information[0].lot_id,
    )

    # check that the data is deleted
    r = client.property_data.get_all_task_properties(task_id=prop_task.id)
    assert isinstance(r[0], TaskPropertyData)
    assert len(r[0].data[0].trials) == 1


def test_add_and_update_property_data_on_inventory(
    client: Albert,
    seeded_inventory: list[BaseTask],
    seeded_data_columns: list[BaseTask],
):
    # add some properties to the inventory
    inv = seeded_inventory[0]
    data_columns = [
        InventoryDataColumn(
            data_column_id=seeded_data_columns[0].id,
            value="55.5",
        ),
        InventoryDataColumn(
            data_column_id=seeded_data_columns[1].id,
            value="66.6",
        ),
    ]
    r = client.property_data.add_properties_to_inventory(
        inventory_id=inv.id, properties=data_columns
    )
    assert isinstance(r[0], InventoryPropertyDataCreate)
    assert r[0].inventory_id == inv.id
    assert r[0].data_columns[0].data_column_id == seeded_data_columns[0].id
    assert r[0].data_columns[0].value == "55.5"


def test_task_property_calculation_evaluation(
    client: Albert,
    seed_prefix: str,
    seeded_inventory,
    seeded_lots,
    seeded_locations,
    seeded_projects,
    seeded_workflows,
):
    calc_task_id = None
    calc_dt_id = None
    calc_dc_ids = []

    try:
        dc_one = client.data_columns.create(
            data_column=DataColumn(name=f"{seed_prefix} - calc col one")
        )
        dc_two = client.data_columns.create(
            data_column=DataColumn(name=f"{seed_prefix} - calc col two")
        )
        dc_calc = client.data_columns.create(
            data_column=DataColumn(name=f"{seed_prefix} - calc col result")
        )
        calc_dc_ids = [dc_one.id, dc_two.id, dc_calc.id]

        calc_dt = client.data_templates.create(
            data_template=DataTemplate(
                name=f"{seed_prefix} - calc dt",
                description="Integration test template for calculated columns.",
                data_column_values=[
                    DataColumnValue(
                        data_column=dc_one,
                    ),
                    DataColumnValue(
                        data_column=dc_two,
                    ),
                ],
            )
        )
        calc_dt_id = calc_dt.id
        sequence_by_id = {col.data_column_id: col.sequence for col in calc_dt.data_column_values}
        seq_one = sequence_by_id[dc_one.id]
        seq_two = sequence_by_id[dc_two.id]
        calc_dt = client.data_templates.add_data_columns(
            data_template_id=calc_dt.id,
            data_columns=[
                DataColumnValue(
                    data_column=dc_calc,
                    calculation=f"={seq_one}+sqrt({seq_two})",
                )
            ],
        )
        sequence_by_id = {col.data_column_id: col.sequence for col in calc_dt.data_column_values}
        seq_calc = sequence_by_id[dc_calc.id]

        lot = next(
            (l for l in seeded_lots if l.inventory_id == seeded_inventory[0].id),
            None,
        )
        workflow = seeded_workflows[0]
        interval_id = (
            workflow.interval_combinations[0].interval_id
            if workflow.interval_combinations
            else "default"
        )

        calc_task = client.tasks.create(
            task=PropertyTask(
                name=f"{seed_prefix} - calc task",
                category=TaskCategory.PROPERTY,
                inventory_information=[
                    TaskInventoryInformation(
                        inventory_id=seeded_inventory[0].id,
                        lot_id=lot.id if lot else None,
                    )
                ],
                parent_id=seeded_inventory[0].id,
                location=seeded_locations[0],
                project=seeded_projects[0],
                blocks=[
                    Block(
                        workflow=[workflow],
                        data_template=[calc_dt],
                    )
                ],
            )
        )
        calc_task_id = calc_task.id
        calc_task = client.tasks.get_by_id(id=calc_task_id)
        block_id = calc_task.blocks[0].id

        result = client.property_data.add_properties_to_task(
            task_id=calc_task_id,
            inventory_id=seeded_inventory[0].id,
            block_id=block_id,
            lot_id=lot.id if lot else None,
            properties=[
                TaskPropertyCreate(
                    interval_combination=interval_id,
                    data_template=calc_dt,
                    data_column=TaskDataColumn(
                        data_column_id=dc_one.id,
                        column_sequence=seq_one,
                    ),
                    value="5",
                ),
                TaskPropertyCreate(
                    interval_combination=interval_id,
                    data_template=calc_dt,
                    data_column=TaskDataColumn(
                        data_column_id=dc_two.id,
                        column_sequence=seq_two,
                    ),
                    value="16",
                ),
            ],
            return_scope="block",
        )

        trial = max(
            (t for t in result[0].data[0].trials if t.data_columns[0].property_data is not None),
            key=lambda t: t.trial_number,
        )
        calc_column = next(c for c in trial.data_columns if c.sequence == seq_calc)
        assert calc_column.property_data is not None
        assert float(calc_column.property_data.value) == pytest.approx(9.0)
    finally:
        if calc_task_id:
            with suppress(NotFoundError):
                client.tasks.delete(id=calc_task_id)
        if calc_dt_id:
            with suppress(NotFoundError):
                client.data_templates.delete(id=calc_dt_id)
        for dc_id in calc_dc_ids:
            with suppress(NotFoundError):
                client.data_columns.delete(id=dc_id)
