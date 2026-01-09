# Tasks

Tasks in Albert Invent are a way to manage and track your daily work and collaborate with colleagues. There are three types of tasks: Batch Tasks, Property Tasks, and General Tasks.

## Import results

This feature enables users to import a .csv file straight into the Data Template of a Property Task allowing them to easily mass enter results without having to type them in manually or copy-paste.

!!! example "Import results from a CSV file"
    ```python
    from albert import Albert
    from albert.resources.data_templates import ImportMode

    client = Albert.from_client_credentials()

    task = client.tasks.import_results(
        task_id="TAS123",
        inventory_id="INV123",
        data_template_id="DT123",
        file_path="path/to/results.csv",
        field_mapping={"comm": "Comments", "Solvent": " Solvent, ppm"},
        mode=ImportMode.CSV,
    )
    print(task)
    ```

!!! example "Import results using a script"
    ```python
    from albert import Albert
    from albert.resources.data_templates import ImportMode

    client = Albert.from_client_credentials()

    task = client.tasks.import_results(
        task_id="TAS123",
        inventory_id="INV123",
        data_template_id="DT123",
        block_id="BLK1",
        file_path="path/to/results.csv",
        mode=ImportMode.SCRIPT,
    )
    ```

!!! warning
    `import_results` deletes existing property data for the matching task/block/inventory/lot/interval
    before writing new values. Use with care if you need to preserve older results.
