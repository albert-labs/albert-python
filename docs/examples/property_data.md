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
                field_mapping={"temperature": "Temperature", "cnt": "Count"},
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

!!! example "Add a new trial row"
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

## Void data row

!!! example "Void task data"
    ```python
    from albert import Albert

    client = Albert.from_client_credentials()

    task_id = "TAS123"
    inventory_id = "INV123"
    block_id = "BLK1"

    client.property_data.void_task_data(
        inventory_id=inventory_id,
        task_id=task_id,
        block_id=block_id,
    )
    ```

!!! example "Void interval data"
    ```python
    from albert import Albert

    client = Albert.from_client_credentials()

    task_id = "TAS123"
    inventory_id = "INV123"
    block_id = "BLK1"

    interval_id = next(
        (
            combo.interval_id
            for combo in client.property_data.check_for_task_data(task_id=task_id)
            if combo.inventory_id == inventory_id and combo.block_id == block_id
        ),
        None,
    )
    if not interval_id:
        raise ValueError("No interval data found for the block/inventory combination.")

    client.property_data.void_interval_data(
        inventory_id=inventory_id,
        task_id=task_id,
        block_id=block_id,
        interval_id=interval_id,
    )
    ```

!!! example "Void trial data"
    ```python
    from albert import Albert

    client = Albert.from_client_credentials()

    task_id = "TAS123"
    inventory_id = "INV123"
    block_id = "BLK1"

    interval_id = next(
        (
            combo.interval_id
            for combo in client.property_data.check_for_task_data(task_id=task_id)
            if combo.inventory_id == inventory_id and combo.block_id == block_id
        ),
        None,
    )
    if not interval_id:
        raise ValueError("No interval data found for the block/inventory combination.")

    client.property_data.void_trial_data(
        inventory_id=inventory_id,
        task_id=task_id,
        block_id=block_id,
        trial_number=2,
        interval_id=interval_id,
    )
    ```

!!! note
    Use the corresponding `unvoid_task_data`, `unvoid_interval_data`, and `unvoid_trial_data`
    methods to unvoid records.
