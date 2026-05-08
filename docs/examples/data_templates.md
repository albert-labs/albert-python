# Data Templates

Data Templates in Albert Invent define how results are captured and structured. They are used to capture clean, structured data about your experiments, such as flexural testing results, tensile testing results, etc.

## Add numeric data column

!!! info "Default validation"
    Data columns added to a template without explicit validation automatically receive `number` as the default datatype. No additional update step is required for basic numeric columns.

!!! example "Create a data column and add it — defaults to NUMBER datatype"
    ```python
    from albert import Albert
    from albert.resources.data_columns import DataColumn
    from albert.resources.data_templates import DataColumnValue

    client = Albert.from_client_credentials()

    data_template_id = "DT123"

    # 1) Create data column
    created_column = client.data_columns.create(
        data_column=DataColumn(name="Viscosity Number"),
    )

    # 2) Add data column to template — validation defaults to NUMBER
    dt = client.data_templates.add_data_columns(
        data_template_id=data_template_id,
        data_columns=[DataColumnValue(data_column_id=created_column.id)],
    )
    print(dt.id)
    ```

## Add numeric data column with range validation

!!! example "Create a data column with a specific numeric range constraint"
    ```python
    from albert import Albert
    from albert.resources.data_columns import DataColumn
    from albert.resources.data_templates import DataColumnValue
    from albert.resources.parameter_groups import DataType, Operator, ValueValidation

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

    # 3) Update template with a range constraint (must be between 0 and 100)
    target = next(x for x in (dt.data_column_values or []) if x.data_column_id == created_column.id)
    target.validation = [ValueValidation(datatype=DataType.NUMBER, operator=Operator.BETWEEN, min="0", max="100")]

    updated_dt = client.data_templates.update(data_template=dt)
    print(updated_dt.id)
    ```

## Add dropdown data column with validation

!!! example "Add two data columns, then set ENUM validation on one"
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

    # 2) Add both columns to template — viscosity defaults to NUMBER validation
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

    # 3) Update appearance column with dropdown (enum) validation
    appearance = next(x for x in (dt.data_column_values or []) if x.data_column_id == appearance_column.id)

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
