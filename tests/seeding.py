from uuid import uuid4

from albert.core.shared.enums import SecurityClass
from albert.core.shared.models.base import EntityLink
from albert.resources.btdataset import BTDataset
from albert.resources.btinsight import BTInsight, BTInsightCategory
from albert.resources.btmodel import BTModel, BTModelSession, BTModelSessionCategory, BTModelState
from albert.resources.cas import Cas, CasCategory
from albert.resources.companies import Company
from albert.resources.custom_fields import (
    CustomField,
    FieldCategory,
    FieldType,
    ServiceType,
)
from albert.resources.data_columns import DataColumn
from albert.resources.data_templates import DataColumnValue, DataTemplate
from albert.resources.inventory import (
    CasAmount,
    InventoryCategory,
    InventoryItem,
    InventoryMinimum,
    InventoryUnitCategory,
)
from albert.resources.links import Link, LinkCategory
from albert.resources.lists import ListItem
from albert.resources.locations import Location
from albert.resources.lots import (
    Lot,
)
from albert.resources.notebooks import (
    BulletedListContent,
    ChecklistBlock,
    ChecklistContent,
    ChecklistItem,
    HeaderBlock,
    HeaderContent,
    ListBlock,
    Notebook,
    NotebookBlock,
    NotebookListItem,
    NumberedListContent,
    ParagraphBlock,
    ParagraphContent,
    TableBlock,
    TableContent,
)
from albert.resources.notes import Note
from albert.resources.parameter_groups import (
    DataType,
    EnumValidationValue,
    Operator,
    ParameterGroup,
    ParameterValue,
    PGType,
    ValueValidation,
)
from albert.resources.parameters import Parameter, ParameterCategory
from albert.resources.pricings import Pricing
from albert.resources.projects import (
    GridDefault,
    Project,
    ProjectClass,
)
from albert.resources.reports import FullAnalyticalReport
from albert.resources.storage_locations import StorageLocation
from albert.resources.tags import Tag
from albert.resources.tasks import (
    BaseTask,
    BatchSizeUnit,
    BatchTask,
    Block,
    GeneralTask,
    PropertyTask,
    TaskCategory,
    TaskInventoryInformation,
    TaskPriority,
)
from albert.resources.units import Unit, UnitCategory
from albert.resources.users import User
from albert.resources.workflows import (
    Interval,
    ParameterGroupSetpoints,
    ParameterSetpoint,
    Workflow,
)

PRELOAD_BTINSIGHT_ID = "INS10"
PRELOAD_BTDATASET_ID = "DST1"
PRELOAD_BTMODELSESSION_ID = "MDS1"
PRELOAD_BTMODEL_ID = "MDL1"


def generate_custom_fields() -> list[CustomField]:
    services = [
        ServiceType.INVENTORIES,
        ServiceType.LOTS,
        ServiceType.PROJECTS,
        ServiceType.TASKS,
        ServiceType.USERS,
        ServiceType.PARAMETER_GROUPS,
        ServiceType.CAS,
    ]

    seeds = []

    for service in services:
        # Create a string-type field for the service
        seeds.append(
            CustomField(
                name=f"test_{service.value}_string_field",
                field_type=FieldType.STRING,
                display_name=f"TEST {service.value.capitalize()} String Field",
                service=service,
            )
        )

        # Create a list-type field for the service
        seeds.append(
            CustomField(
                name=f"test_{service.value}_list_field",
                field_type=FieldType.LIST,
                display_name=f"TEST {service.value.capitalize()} List Field",
                service=service,
                category=FieldCategory.USER_DEFINED,
                min=1,
                max=5,
            )
        )

    return seeds


def generate_list_item_seeds(seeded_custom_fields: list[CustomField]) -> list[ListItem]:
    """
    Generates a list of ListItem seed objects for testing without IDs.

    Returns
    -------
    List[ListItem]
        A list of ListItem objects with different permutations.
    """

    list_custom_fields = [x for x in seeded_custom_fields if x.field_type == FieldType.LIST]
    all_list_items = []
    for custom_field in list_custom_fields:
        for i in range(0, 2):
            all_list_items.append(
                ListItem(
                    name=f"{custom_field.display_name} Option {i}",
                    category=custom_field.category,
                    list_type=custom_field.name,
                )
            )
    return all_list_items


def generate_cas_seeds(
    seed_prefix: str,
    static_custom_fields: list[CustomField],
    static_lists: list[ListItem],
) -> list[Cas]:
    """
    Generates a list of CAS seed objects for testing without IDs.

    Returns
    -------
    List[Cas]
        A list of Cas objects with different permutations.
    """
    cas_string_custom_fields = [
        x
        for x in static_custom_fields
        if x.service == ServiceType.CAS and x.field_type == FieldType.STRING
    ]
    cas_list_custom_fields = [
        x
        for x in static_custom_fields
        if x.service == ServiceType.CAS and x.field_type == FieldType.LIST
    ]

    faux_metadata = {}
    for i, custom_field in enumerate(cas_string_custom_fields):
        faux_metadata[custom_field.name] = f"{seed_prefix} - {custom_field.display_name} {i}"
    for i, custom_field in enumerate(cas_list_custom_fields):
        list_items = [x for x in static_lists if x.list_type == custom_field.name]
        faux_metadata[custom_field.name] = [list_items[i].to_entity_link()]
    return [
        # CAS with basic fields
        Cas(
            number=f"{seed_prefix}-50-00-0",
            description="Formaldehyde",
            category=CasCategory.USER,
            smiles="C=O",
        ),
        Cas(
            number=f"{seed_prefix}-64-17-5",
            description="Ethanol",
            category=CasCategory.TSCA_PUBLIC,
            smiles="C2H5OH",
        ),
        # CAS with optional fields filled out
        Cas(
            number=f"{seed_prefix}-7732-18-5",
            description="Water",
            notes="Common solvent",
            category=CasCategory.NOT_TSCA,
            smiles="O",
            inchi_key="XLYOFNOQVPJJNP-UHFFFAOYSA-N",
            iupac_name="Oxidane",
            name="Water",
        ),
        # CAS with external database reference
        Cas(
            number=f"{seed_prefix}-7440-57-5",
            description="Gold",
            category=CasCategory.EXTERNAL,
            smiles="[Au]",
            inchi_key="N/A",
            iupac_name="Gold",
            name="Gold",
        ),
        # CAS with unknown classification
        Cas(
            number=f"{seed_prefix}-1234-56-7",
            description="Unknown substance",
            category=CasCategory.UNKNOWN,
        ),
        # CAS with Metadata
        Cas(
            number=f"{seed_prefix}-with-metadata-50-00-0",
            description="Formaldehyde",
            category=CasCategory.USER,
            smiles="C=O",
            metadata=faux_metadata,
        ),
    ]


def generate_company_seeds(seed_prefix: str) -> list[Company]:
    """
    Generates a list of Company seed objects for testing without IDs.

    Returns
    -------
    List[Company]
        A list of Company objects with different permutations.
    """

    return [
        # Basic company with name only
        Company(name=f"{seed_prefix} - Acme Corporation"),
        # Company with a full name and additional private attribute (distance)
        Company(name=f"{seed_prefix} - Globex Corporation"),
        # Another company
        Company(name=f"{seed_prefix} - Initech"),
        # One more company with a distance attribute
        Company(name=f"{seed_prefix} - Umbrella Corp"),
    ]


def generate_location_seeds(seed_prefix: str) -> list[Location]:
    """
    Generates a list of Location seed objects for testing without IDs.

    Returns
    -------
    List[Location]
        A list of Location objects with different permutations.
    """

    return [
        # Basic location with required fields (name, latitude, longitude, address)
        Location(
            name=f"{seed_prefix} - Warehouse A",
            latitude=40.7,
            longitude=-74.0,
            address="123 Warehouse St, New York, NY",
        ),
        # Location with full fields including optional country
        Location(
            name=f"{seed_prefix} - Headquarters",
            latitude=37.8,
            longitude=-122.4,
            address="123 Market St, San Francisco, CA",
            country="US",
        ),
        # Location with required fields but without the country
        Location(
            name=f"{seed_prefix} - Remote Office",
            latitude=48.9,
            longitude=2.4,
            address="10 Office Lane, Paris",
        ),
        # Another location with all fields
        Location(
            name=f"{seed_prefix} - Test Site",
            latitude=51.5,
            longitude=-0.1,
            address="Test Facility, London",
            country="GB",
        ),
    ]


def generate_storage_location_seeds(seeded_locations: list[Location]) -> list[StorageLocation]:
    """
    Generates a list of StorageLocation seed objects for testing without IDs.

    Parameters
    ----------
    seeded_locations : List[Location]
        List of seeded Location objects.

    Returns
    -------
    List[StorageLocation]
        A list of StorageLocation objects with different permutations.
    """

    return [
        # Basic storage location with required fields
        StorageLocation(
            name=seeded_locations[0].name,
            location=EntityLink(id=seeded_locations[0].id),
            address="123 Warehouse St, New York, NY",
        ),
        # Storage location with full fields including optional country
        StorageLocation(
            name=seeded_locations[1].name,
            location=EntityLink(id=seeded_locations[1].id),
            address="123 Storage St, San Francisco, CA",
            country="US",
        ),
        # Storage location with required fields but without the country
        StorageLocation(
            name=seeded_locations[2].name,
            location=EntityLink(id=seeded_locations[0].id),
            address="10 Storage Lane, Paris",
        ),
        # Another storage location with all fields
        StorageLocation(
            name=seeded_locations[3].name,
            location=EntityLink(id=seeded_locations[1].id),
            address="Test Storage Facility, London",
            country="GB",
        ),
    ]


def generate_project_seeds(seed_prefix: str, seeded_locations: list[Location]) -> list[Project]:
    """
    Generates a list of Project seed objects for testing without IDs.

    Parameters
    ----------
    seeded_locations : List[Location]
        List of seeded Location objects.

    Returns
    -------
    List[Project]
        A list of Project objects with different permutations.
    """

    return [
        # Project with basic metadata and private classification
        Project(
            description=f"{seed_prefix} - A basic development project.",
            locations=[EntityLink(id=seeded_locations[0].id)],
            project_class=ProjectClass.PRIVATE,
        ),
        # Project with shared classification and advanced metadata
        Project(
            description=f"{seed_prefix} - A public research project focused on new materials.",
            locations=[EntityLink(id=seeded_locations[1].id)],
            project_class=ProjectClass.SHARED,
            grid=GridDefault.WKS,
        ),
        # Project with production category and custom ACLs
        Project(
            description=f"{seed_prefix} - A private production project",
            locations=[
                EntityLink(id=seeded_locations[0].id),
                EntityLink(id=seeded_locations[1].id),
            ],
            project_class=ProjectClass.PRIVATE,
        ),
    ]


def generate_tag_seeds(seed_prefix: str) -> list[Tag]:
    """
    Generates a list of Tag seed objects for testing without IDs.

    Returns
    -------
    List[Tag]
        A list of Tag objects with different permutations.
    """

    return [
        Tag(tag=f"{seed_prefix} - inventory-tag-1"),
        Tag(tag=f"{seed_prefix} - inventory-tag-2"),
        Tag(tag=f"{seed_prefix} - company-tag-1"),
        Tag(tag=f"{seed_prefix} - company-tag-2"),
    ]


def generate_unit_seeds(seed_prefix: str) -> list[Unit]:
    """
    Generates a list of Unit seed objects for testing without IDs.

    Returns
    -------
    List[Unit]
        A list of Unit objects with different permutations.
    """

    return [
        # Basic unit with length category
        Unit(
            name=f"{seed_prefix} - Meter",
            symbol="m",
            synonyms=["Metre"],
            category=UnitCategory.LENGTH,
            verified=True,
        ),
        # Unit with mass category
        Unit(
            name=f"{seed_prefix} - Kilogram",
            symbol="kg",
            category=UnitCategory.MASS,
            verified=True,
        ),
        # Unit with temperature category and synonyms
        Unit(
            name=f"{seed_prefix} - Celsius",
            symbol="°C",
            synonyms=["Centigrade"],
            category=UnitCategory.TEMPERATURE,
            verified=False,
        ),
        # Unit with energy category
        Unit(
            name=f"{seed_prefix} - Joule",
            symbol="J",
            category=UnitCategory.ENERGY,
            verified=True,
        ),
        # Unit with volume category
        Unit(
            name=f"{seed_prefix} - Liter",
            symbol="L",
            synonyms=["Litre"],
            category=UnitCategory.VOLUME,
            verified=True,
        ),
    ]


def generate_data_column_seeds(seed_prefix: str, seeded_units: list[Unit]) -> list[DataColumn]:
    """
    Generates a list of DataColumn seed objects for testing without IDs.

    Returns
    -------
    List[DataColumn]
        A list of DataColumn objects with different permutations.
    """

    return [
        # Basic data column with required fields
        DataColumn(
            name=f"{seed_prefix} - only unit 1",
            unit=EntityLink(id=seeded_units[0].id),
        ),
        # Data column with full fields including optional calculation
        DataColumn(
            name=f"{seed_prefix} - unit and calculation",
            unit=EntityLink(id=seeded_units[1].id),
            calculation="Pressure = Force / Area",
        ),
        # Data column with required fields but without the calculation
        DataColumn(
            name=f"{seed_prefix} - only name",
        ),
        # Another data column with all fields
        DataColumn(
            name=f"{seed_prefix} - only calculation",
            calculation="Mass = Density * Volume",
        ),
    ]


def generate_data_template_seeds(
    seed_prefix: str,
    user: User,
    seeded_data_columns: list[DataColumn],
    seeded_units: list[Unit],
    seeded_tags: list[Tag],
    seeded_parameters: list[Parameter],
) -> list[DataTemplate]:
    """
    Generates a list of DataTemplate seed objects for testing with enhanced complexity.

    Parameters
    ----------
    seed_prefix : str
        A prefix for naming the seeds.
    user : User
        The user associated with the data templates.
    seeded_data_columns : list[DataColumn]
        A list of seeded DataColumn objects.
    seeded_units : list[Unit]
        A list of seeded Unit objects.
    seeded_tags : list[Tag]
        A list of seeded Tag objects.

    Returns
    -------
    list[DataTemplate]
        A list of DataTemplate objects with enhanced complexity.
    """
    return [
        # Basic Data Template with a single column and no validations
        DataTemplate(
            name=f"{seed_prefix} - Basic Data Template",
            description="A basic data template with no validations or tags.",
            data_column_values=[
                DataColumnValue(
                    data_column=seeded_data_columns[0],
                    value="25.0",
                    unit=EntityLink(id=seeded_units[0].id),
                )
            ],
            tags=[seeded_tags[0]],
        ),
        # Data Template with ACL and multiple columns
        DataTemplate(
            name=f"{seed_prefix} - ACL Data Template",
            description="A data template with ACL and multiple columns.",
            data_column_values=[
                DataColumnValue(
                    data_column=seeded_data_columns[0],
                    value="45.0",
                    unit=EntityLink(id=seeded_units[0].id),
                ),
                DataColumnValue(
                    data_column=seeded_data_columns[1],
                    value="100.0",
                    unit=EntityLink(id=seeded_units[1].id),
                ),
            ],
            users_with_access=[user],
        ),
        # Data Template with ENUM validation and tags
        DataTemplate(
            name=f"{seed_prefix} - Enum Validation Template",
            description="A data template with enum validation and tags.",
            data_column_values=[
                DataColumnValue(
                    data_column=seeded_data_columns[0],
                    value="Option1",
                    validation=[
                        ValueValidation(
                            datatype=DataType.ENUM,
                            value=[
                                EnumValidationValue(text="Option1"),
                                EnumValidationValue(text="Option2"),
                            ],
                        )
                    ],
                )
            ],
            tags=seeded_tags[:2],
        ),
        # Data Template with NUMBER validation and a calculation
        DataTemplate(
            name=f"{seed_prefix} - Number Validation Template",
            description="A data template with number validation and a calculation.",
            data_column_values=[
                DataColumnValue(
                    data_column=seeded_data_columns[1],
                    value="50",
                    unit=EntityLink(id=seeded_units[0].id),
                    calculation="Pressure = Force / Area",
                    validation=[
                        ValueValidation(
                            datatype=DataType.NUMBER,
                            min="0",
                            max="100",
                            operator=Operator.BETWEEN,
                        )
                    ],
                )
            ],
            tags=[seeded_tags[1], seeded_tags[2]],
        ),
        # Data Template with STRING validation
        DataTemplate(
            name=f"{seed_prefix} - String Validation Template",
            description="A data template with string validation.",
            data_column_values=[
                DataColumnValue(
                    data_column=seeded_data_columns[2],
                    value="Test String",
                    validation=[
                        ValueValidation(
                            datatype=DataType.STRING,
                        )
                    ],
                )
            ],
        ),
        # Data Template with multiple validations and tags
        DataTemplate(
            name=f"{seed_prefix} - Complex Validation Template",
            description="A data template with multiple validations and tags.",
            data_column_values=[
                DataColumnValue(
                    data_column=seeded_data_columns[0],
                    value="Option1",
                    validation=[
                        ValueValidation(
                            datatype=DataType.ENUM,
                            value=[
                                EnumValidationValue(text="Option1"),
                                EnumValidationValue(text="Option2"),
                            ],
                        )
                    ],
                ),
                DataColumnValue(
                    data_column=seeded_data_columns[1],
                    value="75.0",
                    unit=EntityLink(id=seeded_units[1].id),
                    validation=[
                        ValueValidation(
                            datatype=DataType.NUMBER,
                            min="50",
                            max="100",
                            operator=Operator.BETWEEN,
                        )
                    ],
                ),
            ],
            tags=[seeded_tags[0]],
        ),
        # Data Template with calculations and no validations
        DataTemplate(
            name=f"{seed_prefix} - Calculation Template",
            description="A data template with calculations and no validations.",
            data_column_values=[
                DataColumnValue(
                    data_column=seeded_data_columns[0],
                    calculation="=A1 + B1",
                    unit=EntityLink(id=seeded_units[0].id),
                ),
                DataColumnValue(
                    data_column=seeded_data_columns[1],
                    calculation="=C1 / 2",
                    unit=EntityLink(id=seeded_units[1].id),
                ),
            ],
        ),
        # Data Template with parameters (for PATCH /parameters testing)
        DataTemplate(
            name=f"{seed_prefix} - Parameters Data Template",
            description="A data template with parameters for testing PATCH /parameters.",
            data_column_values=[
                DataColumnValue(
                    data_column=seeded_data_columns[0],
                    value="42.0",
                    unit=EntityLink(id=seeded_units[0].id),
                    validation=[
                        ValueValidation(
                            datatype=DataType.NUMBER,
                            min="0",
                            max="100",
                            operator=Operator.BETWEEN,
                        )
                    ],
                )
            ],
            parameter_values=[
                ParameterValue(
                    id=seeded_parameters[
                        0
                    ].id,  # Replace with a valid seeded Parameter id if available
                    name="Test Parameter",
                    value="123.45",
                    unit=EntityLink(id=seeded_units[0].id),
                    validation=[
                        ValueValidation(
                            datatype=DataType.NUMBER,
                            min="0",
                            max="200",
                            operator=Operator.BETWEEN,
                        )
                    ],
                )
            ],
            tags=[seeded_tags[0]],
        ),
        # Data Template with ENUM validations on both a data column and a parameter
        DataTemplate(
            name=f"{seed_prefix} - Enum Validation Data Template With Parameter",
            description="A data template with ENUM validations on both a data column and a parameter.",
            data_column_values=[
                DataColumnValue(
                    data_column=seeded_data_columns[1],
                    value="OptionA",
                    validation=[
                        ValueValidation(
                            datatype=DataType.ENUM,
                            value=[
                                EnumValidationValue(text="OptionA"),
                                EnumValidationValue(text="OptionB"),
                            ],
                        )
                    ],
                )
            ],
            parameter_values=[
                ParameterValue(
                    id=seeded_parameters[2].id,
                    name="Enum Parameter",
                    value="ParamOption1",
                    validation=[
                        ValueValidation(
                            datatype=DataType.ENUM,
                            value=[
                                EnumValidationValue(text="ParamOption1"),
                                EnumValidationValue(text="ParamOption2"),
                            ],
                        )
                    ],
                ),
                ParameterValue(
                    id=seeded_parameters[3].id,
                    name="Enum Parameter two",
                    value="ParamOption1-1",
                    validation=[
                        ValueValidation(
                            datatype=DataType.ENUM,
                            value=[
                                EnumValidationValue(text="ParamOption1-1"),
                                EnumValidationValue(text="ParamOption1-2"),
                            ],
                        )
                    ],
                ),
            ],
            tags=[seeded_tags[1]],
        ),
    ]


def generate_parameter_seeds(seed_prefix: str) -> list[Parameter]:
    """
    Generates a list of Parameter seed objects for testing without IDs.

    Returns
    -------
    List[Parameter]
        A list of Parameter objects with different permutations.
    """

    return [
        Parameter(
            name=f"{seed_prefix} - Temperature",
        ),
        Parameter(
            name=f"{seed_prefix} - Pressure",
        ),
        Parameter(
            name=f"{seed_prefix} - Volume",
        ),
        Parameter(
            name=f"{seed_prefix} - Mass",
        ),
        Parameter(
            name=f"{seed_prefix} - Length",
        ),
    ]


def generate_parameter_group_seeds(
    seed_prefix: str,
    seeded_parameters: list[Parameter],
    seeded_tags: list[Tag],
    seeded_units: list[Unit],
    static_consumeable_parameter: Parameter,
    static_custom_fields: CustomField,
    static_lists: list[ListItem],
) -> list[ParameterGroup]:
    """
    Generates a list of ParameterGroup seed objects for testing without IDs.

    Parameters
    ----------
    seeded_parameters : List[Parameter]
        List of seeded Parameter objects.

    Returns
    -------
    List[ParameterGroup]
        A list of ParameterGroup objects with different permutations.
    """
    pg_string_custom_fields = [
        x
        for x in static_custom_fields
        if x.service == ServiceType.PARAMETER_GROUPS and x.field_type == FieldType.STRING
    ]
    pg_list_custom_fields = [
        x
        for x in static_custom_fields
        if x.service == ServiceType.PARAMETER_GROUPS and x.field_type == FieldType.LIST
    ]

    faux_metadata = {}
    for i, custom_field in enumerate(pg_string_custom_fields):
        faux_metadata[custom_field.name] = f"{seed_prefix} - {custom_field.display_name} {i}"
    for i, custom_field in enumerate(pg_list_custom_fields):
        list_items = [x for x in static_lists if x.list_type == custom_field.name]
        faux_metadata[custom_field.name] = [list_items[i].to_entity_link()]

    return [
        # Basic ParameterGroup with required fields
        ParameterGroup(
            name=f"{seed_prefix} - General Parameters",
            type=PGType.PROPERTY,
            parameters=[
                ParameterValue(
                    parameter=seeded_parameters[0],
                    value="25.0",
                    unit=seeded_units[1],
                )
            ],
        ),
        ParameterGroup(
            name=f"{seed_prefix} - Enums Parameter Group",
            type=PGType.GENERAL,
            description="A general parameter group with validations and tags.",
            parameters=[
                ParameterValue(
                    parameter=seeded_parameters[0],
                    value="10",
                    unit=EntityLink(id=seeded_units[0].id),
                    validation=[
                        ValueValidation(
                            datatype=DataType.NUMBER,
                            min="0",
                            max="100",
                            operator=Operator.BETWEEN,
                        )
                    ],
                ),
                ParameterValue(
                    parameter=seeded_parameters[2],
                    value="500.0",
                    unit=seeded_units[2],
                    validation=[
                        ValueValidation(
                            datatype=DataType.NUMBER,
                            operator=Operator.GREATER_THAN_OR_EQUAL,
                            value="0.0",
                        )
                    ],
                ),
                ParameterValue(
                    parameter=seeded_parameters[1],
                    value="Option1",
                    validation=[
                        ValueValidation(
                            datatype=DataType.ENUM,
                            value=[
                                EnumValidationValue(text="Option1"),
                                EnumValidationValue(text="Option2"),
                            ],
                        )
                    ],
                ),
            ],
            tags=seeded_tags[:2],
        ),
        ParameterGroup(
            name=f"{seed_prefix} - Numbers Parameter Group",
            type=PGType.GENERAL,
            description="A general parameter group with validations and tags.",
            parameters=[
                ParameterValue(
                    parameter=seeded_parameters[0],
                    value="10",
                    unit=EntityLink(id=seeded_units[0].id),
                    validation=[
                        ValueValidation(
                            datatype=DataType.NUMBER,
                            min="0",
                            max="100",
                            operator=Operator.BETWEEN,
                        )
                    ],
                ),
                ParameterValue(
                    parameter=static_consumeable_parameter, category=ParameterCategory.SPECIAL
                ),
                ParameterValue(
                    parameter=seeded_parameters[2],
                    value="500.0",
                    unit=seeded_units[2],
                    validation=[
                        ValueValidation(
                            datatype=DataType.NUMBER,
                            operator=Operator.GREATER_THAN_OR_EQUAL,
                            value="0.0",
                        )
                    ],
                ),
            ],
            tags=seeded_tags[:2],
        ),
        ParameterGroup(
            name=f"{seed_prefix} - Batch Parameter Group",
            type=PGType.BATCH,
            description="A batch parameter group with no validations.",
            parameters=[
                ParameterValue(
                    parameter=seeded_parameters[1],
                    value="Test Value",
                    unit=EntityLink(id=seeded_units[1].id),
                )
            ],
            tags=seeded_tags[2:],
        ),
        ParameterGroup(
            name=f"{seed_prefix} - Batch Parameters with a consumeable",
            description="Parameters for batch processing",
            type=PGType.BATCH,
            security_class=SecurityClass.RESTRICTED,
            parameters=[
                ParameterValue(
                    parameter=seeded_parameters[1],
                    value="100.0",
                    unit=seeded_units[0],
                ),
                ParameterValue(
                    parameter=seeded_parameters[2],
                    value="500.0",
                    unit=seeded_units[2],
                    validation=[
                        ValueValidation(
                            datatype=DataType.NUMBER,
                            operator=Operator.GREATER_THAN_OR_EQUAL,
                            value="0.0",
                        )
                    ],
                ),
                ParameterValue(
                    parameter=static_consumeable_parameter, category=ParameterCategory.SPECIAL
                ),
            ],
            tags=[seeded_tags[0]],
        ),
        # ParameterGroup with no tags or metadata
        ParameterGroup(
            name=f"{seed_prefix} - Simple Property Parameters",
            type=PGType.PROPERTY,
            parameters=[
                ParameterValue(
                    parameter=seeded_parameters[3],
                    value="75.0",
                    unit=seeded_units[0],
                    category=ParameterCategory.NORMAL,
                ),
                ParameterValue(
                    parameter=seeded_parameters[4],
                    value="2.5",
                    unit=seeded_units[3],
                    category=ParameterCategory.NORMAL,
                ),
            ],
        ),
        ParameterGroup(
            name=f"{seed_prefix} - PG with Metadata",
            type=PGType.PROPERTY,
            parameters=[
                ParameterValue(
                    parameter=seeded_parameters[3],
                    value="75.0",
                    unit=seeded_units[0],
                    category=ParameterCategory.NORMAL,
                ),
                ParameterValue(
                    parameter=seeded_parameters[4],
                    value="2.5",
                    unit=seeded_units[3],
                    category=ParameterCategory.NORMAL,
                ),
            ],
            metadata=faux_metadata,
        ),
    ]


def generate_inventory_seeds(
    seed_prefix: str,
    seeded_cas: list[Cas],
    seeded_tags: list[Tag],
    seeded_companies: list[Company],
    seeded_locations: list[Location],
) -> list[InventoryItem]:
    """Generates a list of InventoryItem seed objects for testing."""
    return [
        InventoryItem(
            name=f"{seed_prefix} - Sodium Chloride",
            description="Common salt used in various applications.",
            category=InventoryCategory.RAW_MATERIALS,
            unit_category=InventoryUnitCategory.MASS,
            security_class=SecurityClass.SHARED,
            company=seeded_companies[0],
        ),
        InventoryItem(
            name=f"{seed_prefix} - Ethanol",
            description="A volatile, flammable liquid used in chemical synthesis.",
            category=InventoryCategory.CONSUMABLES.value,
            unit_category=InventoryUnitCategory.VOLUME.value,
            tags=seeded_tags[0:1],
            cas=[CasAmount(id=seeded_cas[1].id, min=0.98, max=1, cas_smiles=seeded_cas[1].smiles)],
            security_class=SecurityClass.SHARED,
            company=seeded_companies[1].name,  # ensure it knows to use the company object
        ),
        InventoryItem(
            name=f"{seed_prefix} - Hydrochloric Acid",
            description="Strong acid used in various industrial processes.",
            category=InventoryCategory.RAW_MATERIALS,
            unit_category=InventoryUnitCategory.VOLUME,
            cas=[
                # ensure it will reslove the cas obj to an id
                CasAmount(cas=seeded_cas[0], min=0.50, max=1.0, cas_smiles=seeded_cas[0].smiles),
                CasAmount(id=seeded_cas[1].id, min=0.30, max=0.6, cas_smiles=seeded_cas[1].smiles),
            ],
            security_class=SecurityClass.SHARED,
            company=seeded_companies[1],
            minimim=[
                InventoryMinimum(minimum=10.0, location=seeded_locations[0]),
                InventoryMinimum(minimum=20.0, id=seeded_locations[1].id),
            ],
            tags=[seeded_tags[0].tag],  # make sure it knows to use the tag object
        ),
        InventoryItem(
            name=f"{seed_prefix} - Sulfuric Acid",
            description="Common salt used in various applications.",
            category=InventoryCategory.RAW_MATERIALS,
            unit_category=InventoryUnitCategory.MASS,
            security_class=SecurityClass.SHARED,
            company=seeded_companies[0],
            tags=[seeded_tags[0].tag, seeded_tags[1].tag],
        ),
    ]


def generate_lot_seeds(
    seeded_locations: list[Location],
    seeded_inventory: list[InventoryItem],
    seeded_storage_locations: list[StorageLocation],
) -> list[Lot]:
    """
    Generates a list of Lot seed objects for testing without IDs.

    Returns
    -------
    List[Lot]
        A list of Lot objects with different permutations.
    """

    return [
        # Basic Lot with metadata and default status
        Lot(
            inventory_id=seeded_inventory[0].id,
            storage_location=EntityLink(id=seeded_storage_locations[0].id),
            initial_quantity=100.0,
            cost=50.0,
            inventory_on_hand=90.0,
            lot_number="LOT001",
            expiration_date="2025-12-31",
            manufacturer_lot_number="MLN12345",
            location=EntityLink(id=seeded_locations[1].id),
            notes="This is a test lot with default status.",
            external_barcode_id=str(uuid4()),
        ),
        # Lot with active status and no metadata
        Lot(
            inventory_id=seeded_inventory[0].id,
            storage_location=EntityLink(id=seeded_storage_locations[1].id),
            initial_quantity=500.0,
            cost=200.0,
            inventory_on_hand=400.0,
            lot_number="LOT002",
            expiration_date="2026-01-31",
            manufacturer_lot_number="MLN67890",
            location=EntityLink(id=seeded_locations[0].id),
            notes="This is an active lot with no metadata.",
            external_barcode_id=str(uuid4()),
        ),
        # Lot with quarantined status and full metadata
        Lot(
            inventory_id=seeded_inventory[1].id,
            storage_location=EntityLink(id=seeded_storage_locations[1].id),
            initial_quantity=1000.0,
            cost=750.0,
            inventory_on_hand=1000.0,
            lot_number="LOT003",
            expiration_date="2024-11-30",
            manufacturer_lot_number="MLN112233",
            location=EntityLink(id=seeded_locations[1].id),
            notes="This lot is quarantined due to quality issues.",
            external_barcode_id=str(uuid4()),
        ),
    ]


def generate_pricing_seeds(
    seed_prefix: str,
    seeded_inventory: list[InventoryItem],
    seeded_locations: list[Location],
) -> list[Pricing]:
    return [
        Pricing(
            inventory_id=seeded_inventory[0].id,
            company=seeded_inventory[0].company,
            location=seeded_locations[0],
            description=f"{seed_prefix} - Pricing seed 1",
            price=42.0,
        ),
        Pricing(
            inventory_id=seeded_inventory[0].id,
            company=seeded_inventory[0].company,
            location=seeded_locations[1],
            description=f"{seed_prefix} - Pricing seed 2",
            price=50.0,
        ),
        Pricing(
            inventory_id=seeded_inventory[1].id,
            company=seeded_inventory[2].company,
            location=seeded_locations[0],
            description=f"{seed_prefix} - Pricing seed 3",
            price=10.50,
        ),
        Pricing(
            inventory_id=seeded_inventory[2].id,
            company=seeded_inventory[2].company,
            location=seeded_locations[1],
            description=f"{seed_prefix} - Pricing seed 4",
            price=5375.97,
        ),
    ]


def generate_workflow_seeds(
    seed_prefix: str,
    seeded_parameter_groups: list[ParameterGroup],
    seeded_parameters: list[Parameter],
    static_consumeable_parameter: Parameter,
    seeded_inventory: list[InventoryItem],
) -> list[Workflow]:
    def _get_param_from_id(seeded_parameters, param_id):
        for x in seeded_parameters:
            if x.id == param_id:
                return x

    consumeable_inv = [x for x in seeded_inventory if x.category == InventoryCategory.CONSUMABLES][
        0
    ]
    return [
        Workflow(
            name=f"{seed_prefix} - Workflow 1",
            parameter_group_setpoints=[
                ParameterGroupSetpoints(
                    parameter_group=seeded_parameter_groups[0],
                    parameter_setpoints=[
                        ParameterSetpoint(
                            parameter_id=seeded_parameter_groups[0].parameters[0].id,
                            value="25.0",
                            unit=seeded_parameter_groups[0].parameters[0].unit,
                        ),
                    ],
                )
            ],
        ),
        Workflow(
            name=f"{seed_prefix} - Workflow 2 Equipment",
            parameter_group_setpoints=[
                ParameterGroupSetpoints(
                    parameter_group=seeded_parameter_groups[2],
                    parameter_setpoints=[
                        ParameterSetpoint(
                            parameter_id=seeded_parameter_groups[2].parameters[0].id,
                            value="25.0",
                            unit=seeded_parameter_groups[2].parameters[0].unit,
                        ),
                        ParameterSetpoint(
                            parameter_id=static_consumeable_parameter.id,
                            short_name=f"{seed_prefix[0:6]} - Equipment",
                            value=consumeable_inv.to_entity_link(),
                            category=ParameterCategory.SPECIAL,
                        ),
                        ParameterSetpoint(
                            parameter=_get_param_from_id(
                                seeded_parameters, seeded_parameter_groups[2].parameters[2].id
                            ),  # Make sure setting from the parameter works
                            intervals=[
                                Interval(
                                    value="1.1", unit=seeded_parameter_groups[2].parameters[2].unit
                                ),
                                Interval(
                                    value="2.2", unit=seeded_parameter_groups[2].parameters[2].unit
                                ),
                            ],
                        ),
                    ],
                )
            ],
        ),
        Workflow(
            name=f"{seed_prefix} - Workflow 3",
            parameter_group_setpoints=[
                ParameterGroupSetpoints(
                    parameter_group=seeded_parameter_groups[2],
                    parameter_setpoints=[
                        ParameterSetpoint(
                            parameter=_get_param_from_id(
                                seeded_parameters, seeded_parameter_groups[2].parameters[0].id
                            ),  # make sure setting from a parameter works
                            value="12.2",
                            unit=seeded_parameter_groups[2].parameters[0].unit,
                            categoty=ParameterCategory.NORMAL,
                        ),
                        ParameterSetpoint(
                            parameter_id=seeded_parameter_groups[2].parameters[1].id,
                            intervals=[
                                Interval(
                                    value="1.1", unit=seeded_parameter_groups[2].parameters[1].unit
                                ),
                                Interval(
                                    value="2.2", unit=seeded_parameter_groups[2].parameters[1].unit
                                ),
                            ],
                        ),
                    ],
                )
            ],
        ),
    ]


def generate_notebook_block_seeds() -> list[NotebookBlock]:
    return [
        HeaderBlock(content=HeaderContent(level=1, text="I am a header1 block.")),
        HeaderBlock(content=HeaderContent(level=2, text="I am a header2 block.")),
        HeaderBlock(content=HeaderContent(level=3, text="I am a header3 block.")),
        ParagraphBlock(content=ParagraphContent(text="I am a paragraph block.")),
        TableBlock(
            content=TableContent(
                content=[
                    ["row1-col1", None, "row1-col3"],
                    [None, "row2-col2", None],
                    ["row3-col1", None, "row3-col3"],
                ]
            )
        ),
        ChecklistBlock(
            content=ChecklistContent(
                items=[
                    ChecklistItem(checked=True, text="I am checked."),
                    ChecklistItem(checked=False, text="I am not checked."),
                    ChecklistItem(checked=True, text="I am also checked."),
                ]
            )
        ),
        ListBlock(
            content=BulletedListContent(
                items=[
                    NotebookListItem(content="I", items=[NotebookListItem(content="subbullet 1")]),
                    NotebookListItem(
                        content="am", items=[NotebookListItem(content="subbullet 2")]
                    ),
                    NotebookListItem(content="a", items=[NotebookListItem(content="subbullet 3")]),
                    NotebookListItem(
                        content="bulleted", items=[NotebookListItem(content="subbullet 4")]
                    ),
                    NotebookListItem(
                        content="list", items=[NotebookListItem(content="subbullet 5")]
                    ),
                ]
            )
        ),
        ListBlock(
            content=NumberedListContent(
                items=[
                    NotebookListItem(content="I", items=[NotebookListItem(content="subnumber 1")]),
                    NotebookListItem(
                        content="am", items=[NotebookListItem(content="subnumber 2")]
                    ),
                    NotebookListItem(content="a", items=[NotebookListItem(content="subnumber 3")]),
                    NotebookListItem(
                        content="numbered", items=[NotebookListItem(content="subnumber 4")]
                    ),
                    NotebookListItem(
                        content="list", items=[NotebookListItem(content="subnumber 5")]
                    ),
                ]
            )
        ),
    ]


def generate_notebook_seeds(seed_prefix: str, seeded_projects: list[Project]) -> list[Notebook]:
    seed_project = seeded_projects[0]
    return [
        Notebook(
            name=f"{seed_prefix} - Project Notebook 1",
            parent_id=seed_project.id,
            blocks=[],
        ),
        # TODO: Add another notebook with a General Task parent
    ]


def generate_task_seeds(
    seed_prefix: str,
    user: User,
    seeded_inventory,
    seeded_lots,
    seeded_projects,
    seeded_locations,
    seeded_data_templates,
    seeded_workflows,
    seeded_products,
    static_lists: list[ListItem],
    static_custom_fields: list[CustomField],
) -> list[BaseTask]:
    task_string_custom_fields = [
        x
        for x in static_custom_fields
        if x.service == ServiceType.TASKS and x.field_type == FieldType.STRING
    ]
    task_list_custom_fields = [
        x
        for x in static_custom_fields
        if x.service == ServiceType.TASKS and x.field_type == FieldType.LIST
    ]
    faux_metadata = {}
    for i, custom_field in enumerate(task_string_custom_fields):
        faux_metadata[custom_field.name] = f"{seed_prefix} - {custom_field.display_name} {i}"
    for i, custom_field in enumerate(task_list_custom_fields):
        list_items = [x for x in static_lists if x.list_type == custom_field.name]
        faux_metadata[custom_field.name] = [list_items[i].to_entity_link()]

    formulation_proj = [x for x in seeded_projects if x.id == seeded_products[2].project_id][0]
    return [
        # Property Task 1
        PropertyTask(
            name=f"{seed_prefix} - Property Task 1",
            category=TaskCategory.PROPERTY,
            inventory_information=[
                TaskInventoryInformation(
                    inventory_id=seeded_inventory[0].id,
                    lot_id=seeded_lots[0].id,
                )
            ],
            parent_id=seeded_inventory[0].id,
            location=seeded_locations[0],
            priority=TaskPriority.MEDIUM,
            project=seeded_projects[0],
            blocks=[
                Block(
                    workflow=[seeded_workflows[0]],
                    data_template=[seeded_data_templates[0]],
                )
            ],
            assigned_to=user,
            due_date="2024-10-31",
        ),
        # Property Task 2
        PropertyTask(
            name=f"{seed_prefix} - Property Task 2",
            category=TaskCategory.PROPERTY,
            inventory_information=[
                TaskInventoryInformation(
                    inventory_id=seeded_inventory[1].id,
                    lot_id=(
                        [l for l in seeded_lots if l.inventory_id == seeded_inventory[1].id][0].id
                    ),
                )
            ],
            priority=TaskPriority.HIGH,
            blocks=[
                Block(
                    workflow=[seeded_workflows[1]],
                    data_template=[seeded_data_templates[1]],
                )
            ],
            due_date="2024-10-31",
            location=seeded_locations[1],
        ),
        # General Task 1
        GeneralTask(
            name=f"{seed_prefix} - General Task with metadata",
            category=TaskCategory.GENERAL,
            inventory_information=[
                TaskInventoryInformation(
                    inventory_id=seeded_inventory[2].id,
                )
            ],
            priority=TaskPriority.HIGH,
            due_date="2024-10-31",
            location=seeded_locations[1],
            metadata=faux_metadata,
        ),
        # Batch Task 1
        # Use the Formulations used in #tests/resources/test_sheets/py defined as seeded_products
        BatchTask(
            name=f"{seed_prefix} - Batch Task 1",
            category=TaskCategory.BATCH,
            batch_size_unit=BatchSizeUnit.KILOGRAMS,
            inventory_information=[
                TaskInventoryInformation(
                    inventory_id=seeded_products[2].id,
                    batch_size=100.0,
                )
            ],
            location=seeded_locations[1],
            priority=TaskPriority.LOW,
            project=formulation_proj,
            parent_id=formulation_proj.id,
            assigned_to=user,
            start_date="2024-10-01",
            due_date="2024-10-31",
            workflows=[seeded_workflows[1]],
        ),
        # Batch Task 2
        BatchTask(
            name=f"{seed_prefix} - Batch Task 2",
            category=TaskCategory.BATCH,
            batch_size_unit=BatchSizeUnit.GRAMS,
            inventory_information=[
                TaskInventoryInformation(
                    inventory_id=seeded_products[1].id,
                    batch_size=250.0,
                )
            ],
            location=seeded_locations[2],
            priority=TaskPriority.MEDIUM,
            project=formulation_proj,
            parent_id=formulation_proj.id,
            assigned_to=user,
            start_date="2024-10-01",
            due_date="2024-10-31",
        ),
    ]


def generate_note_seeds(
    seeded_tasks: list[BaseTask], seeded_inventory: list[InventoryItem], seed_prefix: str
):
    task_note = Note(
        parent_id=seeded_tasks[0].id,
        note=f"{seed_prefix} This is a note for a task",
    )
    inv_note = Note(
        parent_id=seeded_inventory[0].id,
        note=f"{seed_prefix} This is a note for an inventory item",
    )
    return [task_note, inv_note]


def generate_link_seeds(seeded_tasks: list[BaseTask]):
    # NOTE: As more Links are available, we should add tests for them
    links = []
    for task in seeded_tasks[1:]:
        links.append(
            Link(
                parent=seeded_tasks[0].to_entity_link(),
                child=task.to_entity_link(),
                category=LinkCategory.LINKED_TASK,
            )
        )
    return links


def generate_btdataset_seed(seed_prefix: str) -> BTDataset:
    return BTDataset(
        name=f"{seed_prefix} - Test BT Dataset",
    )


def generate_btmodelsession_seed(seed_prefix: str, seeded_btdataset: BTDataset) -> BTModelSession:
    return BTModelSession(
        name=f"{seed_prefix} - Test BT Model Session",
        category=BTModelSessionCategory.ALBERT_MODEL,
        dataset_id=seeded_btdataset.id,
    )


def generate_btmodel_seed(seed_prefix: str, seeded_btdataset: BTDataset) -> BTModel:
    return BTModel(
        name=f"{seed_prefix} - Test BT Model",
        target=["output1", "output2"],
        state=BTModelState.QUEUED,
        dataset_id=seeded_btdataset.id,
    )


def generate_btinsight_seed(
    seed_prefix: str,
    seeded_btdataset: BTDataset,
    seeded_btmodelsession: BTModel,
) -> BTInsight:
    return BTInsight(
        name=f"{seed_prefix} - Test BT Insight",
        dataset_id=seeded_btdataset.id,
        model_session_id=seeded_btmodelsession.id,
        category=BTInsightCategory.CUSTOM_OPTIMIZER,
        metadata={},
    )


def generate_report_seeds(
    seed_prefix: str, seeded_projects: list[Project]
) -> list[FullAnalyticalReport]:
    """
    Generates a list of FullAnalyticalReport seed objects for testing.

    Parameters
    ----------
    seed_prefix : str
        Prefix to use for generating unique names.
    seeded_projects : list[Project]
        List of seeded Project objects to reference in reports.

    Returns
    -------
    list[FullAnalyticalReport]
        A list of FullAnalyticalReport objects with different configurations.
    """
    project_ids = [project.id for project in seeded_projects]

    return [
        # Basic analytical report
        FullAnalyticalReport(
            report_type_id="ALB#RET42",
            name=f"{seed_prefix} - Basic Analytical Report",
            description=f"{seed_prefix} - A basic analytical report for testing",
            input_data={"project": project_ids},
            project_id=seeded_projects[0].id if seeded_projects else None,
        ),
    ]
