# Data Templates

Data Templates in Albert Invent define how results are captured and structured. They are used to capture clean, structured data about your experiments, such as flexural testing results, tensile testing results, etc.

## Add numeric data column

!!! example "Create a data column, add it, then set NUMBER datatype"
    ```python
    from albert import Albert
    from albert.resources.data_columns import DataColumn
    from albert.resources.data_templates import DataColumnValue
    from albert.resources.parameter_groups import DataType, ValueValidation

    client = Albert.from_client_credentials()

    data_template_id = "DT123"

    # 1) Create data column
    created_column = client.data_columns.create(
        data_column=DataColumn(name="Viscosity Number"),
    )

    # 2) Add data column to template
    dt = client.data_templates.add_data_columns(
        data_template_id=data_template_id,
        data_columns=[DataColumnValue(data_column_id=created_column.id)],
    )

    # 3) Update template and set NUMBER datatype
    target = next(x for x in (dt.data_column_values or []) if x.data_column_id == created_column.id)
    target.validation = [ValueValidation(datatype=DataType.NUMBER)]

    updated_dt = client.data_templates.update(data_template=dt)
    print(updated_dt.id)
    ```

## Add dropdown data column with validation

!!! example "Add two data columns, then set ENUM and NUMBER validations"
    ```python
    from albert import Albert
    from albert.resources.data_columns import DataColumn
    from albert.resources.data_templates import DataColumnValue
    from albert.resources.parameter_groups import (
        DataType,
        EnumValidationValue,
        ValueValidation,
    )

    client = Albert.from_client_credentials()

    data_template_id = "DT123"

    # 1) Create data columns
    appearance_column = client.data_columns.create(
        data_column=DataColumn(name="Appearance"),
    )
    viscosity_column = client.data_columns.create(
        data_column=DataColumn(name="Viscosity Number"),
    )

    # 2) Add both columns to template
    dt = client.data_templates.add_data_columns(
        data_template_id=data_template_id,
        data_columns=[
            DataColumnValue(
                data_column_id=appearance_column.id,
            ),
            DataColumnValue(
                data_column_id=viscosity_column.id,
            ),
        ],
    )

    # 3) Update template with dropdown (enum) + number validations
    appearance = next(x for x in (dt.data_column_values or []) if x.data_column_id == appearance_column.id)
    viscosity = next(x for x in (dt.data_column_values or []) if x.data_column_id == viscosity_column.id)

    appearance.validation = [
        ValueValidation(
            datatype=DataType.ENUM,
            value=[
                EnumValidationValue(text="Clear"),
                EnumValidationValue(text="Cloudy"),
                EnumValidationValue(text="Opaque"),
            ],
        )
    ]
    viscosity.validation = [ValueValidation(datatype=DataType.NUMBER)]

    updated_dt = client.data_templates.update(data_template=dt)
    print(updated_dt.id)
    ```

## Add function data column

!!! example "Set a data column's value to a formula that references other columns"
    ```python
    from albert import Albert
    from albert.resources.data_columns import DataColumn
    from albert.resources.data_templates import DataColumnValue

    client = Albert.from_client_credentials()

    data_template_id = "DT123"
    formula = "=COL4+COL7+COL9"

    # 1) Create data column
    created_column = client.data_columns.create(
        data_column=DataColumn(name="Derived Result"),
    )

    # 2) Add to data template
    dt = client.data_templates.add_data_columns(
        data_template_id=data_template_id,
        data_columns=[DataColumnValue(data_column_id=created_column.id)],
    )

    # 3) Set value + calculation
    target = next(x for x in (dt.data_column_values or []) if x.data_column_id == created_column.id)
    target.value = "100"
    target.calculation = formula

    updated_dt = client.data_templates.update(data_template=dt)
    print(updated_dt.id)
    ```
