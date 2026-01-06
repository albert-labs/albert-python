# Property Data

Property data refers to the results collected from a Property Task in Albert. This data is captured using Data Templates, which allow for the collection of clean, structured data about your experiments.

## Update an existing trial row

!!! example "Update a trial row"
    ```python
    from albert import Albert
    from albert.resources.property_data import (
        CurvePropertyValue,
        ImagePropertyValue,
        TaskDataColumn,
        TaskPropertyCreate,
    )

    client = Albert.from_client_credentials()

    task_id = "TAS123"
    inventory_id = "INV123"
    block_id = "BLK1"

    task_ptd = client.property_data.get_task_block_properties(
        inventory_id=inventory_id,
        task_id=task_id,
        block_id=block_id,
    )
    dt = task_ptd.data_template

    # trial_number maps to the row number in the task data.
    # when provided, it updates that row for the given columns.
    properties = [
        TaskPropertyCreate(
            data_column=TaskDataColumn(data_column_id="DAC123", column_sequence="COL4"),
            value="10",
            trial_number=2,
            data_template=dt,
        ),
        TaskPropertyCreate(
            data_column=TaskDataColumn(data_column_id="DAC456", column_sequence="COL5"),
            value="enum2",
            trial_number=1,
            data_template=dt,
        ),
        # image property data
        TaskPropertyCreate(
            data_column=TaskDataColumn(data_column_id="DAC789", column_sequence="COL1"),
            value=ImagePropertyValue(file_path="path/to/image.png"),
            trial_number=1,
            data_template=dt,
        ),
        # curve property data (CSV import by default)
        TaskPropertyCreate(
            data_column=TaskDataColumn(data_column_id="DAC313", column_sequence="COL3"),
            value=CurvePropertyValue(
                file_path="path/to/curve.csv",
                field_mapping={"Temperature": "dac1957", " Count": "dac517"},
            ),
            trial_number=1,
            data_template=dt,
        ),
    ]

    client.property_data.update_or_create_task_properties(
        inventory_id=inventory_id,
        task_id=task_id,
        block_id=block_id,
        properties=properties,
        return_scope="block",
    )
    ```

## Add a new trial row

!!! example "Add a new row"
    ```python
    from albert.resources.property_data import TaskDataColumn, TaskPropertyCreate

    task_ptd = client.property_data.get_task_block_properties(
        inventory_id=inventory_id,
        task_id=task_id,
        block_id=block_id,
    )
    dt = task_ptd.data_template

    # Omitting trial_number creates a new row in the task data table.
    new_row = [
        TaskPropertyCreate(
            data_column=TaskDataColumn(data_column_id="DAC123", column_sequence="COL4"),
            value="25",
            data_template=dt,
        )
    ]

    client.property_data.update_or_create_task_properties(
        inventory_id=inventory_id,
        task_id=task_id,
        block_id=block_id,
        properties=new_row,
        return_scope="block",
    )
    ```
