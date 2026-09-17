# Parameter Groups

Parameter Groups in Albert Invent define reusable sets of parameters that can be attached to inventory items, projects, and other entities to capture structured measurements or attributes.

## Add a parameter with dropdown (ENUM) validation

!!! example "Append a new parameter with predefined enum options to an existing parameter group"
    ```python
    from albert import Albert
    from albert.resources.parameter_groups import (
        DataType,
        EnumValidationValue,
        ParameterValue,
        ValueValidation,
    )
    from albert.resources.parameters import Parameter

    client = Albert.from_client_credentials()

    parameter_group_id = "PRG123"

    # 1) Fetch the existing parameter group
    pg = client.parameter_groups.get_by_id(id=parameter_group_id)

    # 2) Create or retrieve the parameter to add
    parameter = client.parameters.get_or_create(
        parameter=Parameter(name="Appearance"),
    )

    # 3) Append the parameter with ENUM validation
    pg.parameters.append(
        ParameterValue(
            parameter=parameter,
            validation=[
                ValueValidation(
                    datatype=DataType.ENUM,
                    value=[
                        EnumValidationValue(text="Clear"),
                        EnumValidationValue(text="Cloudy"),
                        EnumValidationValue(text="Opaque"),
                    ],
                )
            ],
        )
    )

    updated_pg = client.parameter_groups.update(parameter_group=pg)
    print(updated_pg.id)
    ```
