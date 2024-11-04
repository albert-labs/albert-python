from uuid import uuid4

from albert.resources.base import BaseEntityLink, SecurityClass
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
from albert.resources.lists import ListItem
from albert.resources.locations import Location
from albert.resources.lots import (
    Lot,
)
from albert.resources.parameter_groups import ParameterGroup, ParameterValue, PGType
from albert.resources.parameters import Parameter, ParameterCategory
from albert.resources.pricings import Pricing
from albert.resources.projects import (
    GridDefault,
    Project,
    ProjectClass,
)
from albert.resources.roles import Role
from albert.resources.storage_locations import StorageLocation
from albert.resources.tags import Tag
from albert.resources.teams import Team
from albert.resources.units import Unit, UnitCategory
from albert.resources.users import User, UserClass
from albert.resources.workflows import (
    Interval,
    ParameterGroupSetpoints,
    ParameterSetpoint,
    Workflow,
)


def generate_custom_fields() -> list[CustomField]:
    services = [
        ServiceType.INVENTORIES,
        ServiceType.LOTS,
        ServiceType.PROJECTS,
        ServiceType.TASKS,
        ServiceType.USERS,
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


def generate_cas_seeds() -> list[Cas]:
    """
    Generates a list of CAS seed objects for testing without IDs.

    Returns
    -------
    List[Cas]
        A list of Cas objects with different permutations.
    """

    return [
        # CAS with basic fields
        Cas(
            number="TEST-50-00-0",
            description="Formaldehyde",
            category=CasCategory.USER,
            smiles="C=O",
        ),
        Cas(
            number="TEST-64-17-5",
            description="Ethanol",
            category=CasCategory.TSCA_PUBLIC,
            smiles="C2H5OH",
        ),
        # CAS with optional fields filled out
        Cas(
            number="TEST-7732-18-5",
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
            number="TEST-7440-57-5",
            description="Gold",
            category=CasCategory.EXTERNAL,
            smiles="[Au]",
            inchi_key="N/A",
            iupac_name="Gold",
            name="Gold",
        ),
        # CAS with unknown classification
        Cas(
            number="TEST-1234-56-7", description="Unknown substance", category=CasCategory.UNKNOWN
        ),
    ]


def generate_company_seeds() -> list[Company]:
    """
    Generates a list of Company seed objects for testing without IDs.

    Returns
    -------
    List[Company]
        A list of Company objects with different permutations.
    """

    return [
        # Basic company with name only
        Company(name="TEST - Acme Corporation"),
        # Company with a full name and additional private attribute (distance)
        Company(name="TEST - Globex Corporation"),
        # Another company
        Company(name="TEST - Initech"),
        # One more company with a distance attribute
        Company(name="TEST - Umbrella Corp"),
    ]


def generate_location_seeds() -> list[Location]:
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
            name="TEST - Warehouse A",
            latitude=40.7,
            longitude=-74.0,
            address="123 Warehouse St, New York, NY",
        ),
        # Location with full fields including optional country
        Location(
            name="TEST - Headquarters",
            latitude=37.8,
            longitude=-122.4,
            address="123 Market St, San Francisco, CA",
            country="US",
        ),
        # Location with required fields but without the country
        Location(
            name="TEST - Remote Office",
            latitude=48.9,
            longitude=2.4,
            address="10 Office Lane, Paris",
        ),
        # Another location with all fields
        Location(
            name="TEST - Test Site",
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
            name="TEST - Warehouse A",
            location=BaseEntityLink(id=seeded_locations[0].id),
            address="123 Warehouse St, New York, NY",
        ),
        # Storage location with full fields including optional country
        StorageLocation(
            name="TEST - Storage Room 1",
            location=BaseEntityLink(id=seeded_locations[1].id),
            address="123 Storage St, San Francisco, CA",
            country="US",
        ),
        # Storage location with required fields but without the country
        StorageLocation(
            name="TEST - Storage Room 2",
            location=BaseEntityLink(id=seeded_locations[0].id),
            address="10 Storage Lane, Paris",
        ),
        # Another storage location with all fields
        StorageLocation(
            name="TEST - Storage Room 3",
            location=BaseEntityLink(id=seeded_locations[1].id),
            address="Test Storage Facility, London",
            country="GB",
        ),
    ]


def generate_project_seeds(seeded_locations: list[Location]) -> list[Project]:
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
        # Project with basic metadata and public classification
        Project(
            description="TEST - A basic development project.",
            locations=[BaseEntityLink(id=seeded_locations[0].id)],
            project_class=ProjectClass.PRIVATE,
            # metadata=Metadata(
            #     adpNumber="adp123",
            # ),
        ),
        # Project with shared classification and advanced metadata
        Project(
            description="TEST - A public research project focused on new materials.",
            locations=[BaseEntityLink(id=seeded_locations[1].id)],
            project_class=ProjectClass.PUBLIC,
            grid=GridDefault.WKS,
        ),
        # Project with production category and custom ACLs
        Project(
            description="TEST - A private production project",
            locations=[
                BaseEntityLink(id=seeded_locations[0].id),
                BaseEntityLink(id=seeded_locations[1].id),
            ],
            project_class=ProjectClass.PRIVATE,
        ),
    ]


def generate_tag_seeds() -> list[Tag]:
    """
    Generates a list of Tag seed objects for testing without IDs.

    Returns
    -------
    List[Tag]
        A list of Tag objects with different permutations.
    """

    return [
        Tag(tag="TEST-TAG-inventory-tag-1"),
        Tag(tag="TEST-TAG-inventory-tag-2"),
        Tag(tag="TEST-TAG-company-tag-1"),
        Tag(tag="TEST-TAG-company-tag-2"),
    ]


def generate_unit_seeds() -> list[Unit]:
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
            name="TEST - Meter",
            symbol="m",
            synonyms=["Metre"],
            category=UnitCategory.LENGTH,
            verified=True,
        ),
        # Unit with mass category
        Unit(name="TEST - Kilogram", symbol="kg", category=UnitCategory.MASS, verified=True),
        # Unit with temperature category and synonyms
        Unit(
            name="TEST - Celsius",
            symbol="°C",
            synonyms=["Centigrade"],
            category=UnitCategory.TEMPERATURE,
            verified=False,
        ),
        # Unit with energy category
        Unit(name="TEST - Joule", symbol="J", category=UnitCategory.ENERGY, verified=True),
        # Unit with volume category
        Unit(
            name="TEST - Liter",
            symbol="L",
            synonyms=["Litre"],
            category=UnitCategory.VOLUME,
            verified=True,
        ),
    ]


def generate_data_column_seeds(seeded_units) -> list[DataColumn]:
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
            name="TEST - only unit 1",
            unit=BaseEntityLink(id=seeded_units[0].id),
        ),
        # Data column with full fields including optional calculation
        DataColumn(
            name="TEST - unit and calculation",
            unit=BaseEntityLink(id=seeded_units[1].id),
            calculation="Pressure = Force / Area",
        ),
        # Data column with required fields but without the calculation
        DataColumn(
            name="TEST - only name",
        ),
        # Another data column with all fields
        DataColumn(
            name="TEST - only calculation",
            calculation="Mass = Density * Volume",
        ),
    ]


def generate_data_template_seeds(
    seeded_data_columns: list[DataColumn], seeded_units: list[Unit], seeded_users: list[User]
) -> list[DataTemplate]:
    return [
        DataTemplate(
            name="TEST - Basic Data Template",
            description="A basic data template with no metadata.",
            data_column_values=[
                DataColumnValue(
                    data_column=seeded_data_columns[0],
                    value="25.0",
                    unit=BaseEntityLink(id=seeded_units[0].id),
                )
            ],
        ),
        DataTemplate(
            name="TEST - ACL Data Template",
            description="A basic data template with no metadata.",
            data_column_values=[
                DataColumnValue(
                    data_column=seeded_data_columns[0],
                    value="45.0",
                    unit=seeded_units[0],
                )
            ],
            users_with_access=[seeded_users[0], seeded_users[1]],
        ),
        DataTemplate(
            name="TEST - Data Template with Calculations",
            description="A data template with calculations.",
            data_column_values=[
                DataColumnValue(
                    data_column_id=seeded_data_columns[0].id,
                    unit=seeded_units[0],
                ),
                DataColumnValue(
                    data_column=seeded_data_columns[1],
                    calculation=f"={seeded_data_columns[0].name}/2",
                    unit=seeded_units[0],
                ),
            ],
        ),
    ]


def generate_user_seeds(seeded_locations: list[Location], seeded_roles: list[Role]) -> list[User]:
    """
    Generates a list of User seed objects for testing without IDs.

    Parameters
    ----------
    seeded_locations : List[Location]
        List of seeded Location objects.
    seeded_roles : List[Role]
        List of seeded Role objects.

    Returns
    -------
    List[User]
        A list of User objects with different permutations.
    """

    return [
        # Basic standard user with metadata and one role
        User(
            name="TEST - Alice Smith",
            location=seeded_locations[0],
            email="testcase_alice.smith@example.com",
            roles=[seeded_roles[0]],
            user_class=UserClass.STANDARD,
        ),
        # Privileged user with no metadata
        User(
            name="TEST - Bob Johnson",
            location=seeded_locations[1],
            email="testcase_bob.johnson@example.com",
            roles=[seeded_roles[0]],
            user_class=UserClass.STANDARD,
        ),
        # Admin user with full metadata
        User(
            name="TEST - Charlie Brown",
            location=seeded_locations[2],
            email="testcase_charlie.brown@example.com",
            roles=[seeded_roles[0]],
            user_class=UserClass.STANDARD,
        ),
    ]


def generate_parameter_seeds() -> list[Parameter]:
    """
    Generates a list of Parameter seed objects for testing without IDs.

    Returns
    -------
    List[Parameter]
        A list of Parameter objects with different permutations.
    """

    return [
        Parameter(name="TEST - Temperature", category=ParameterCategory.NORMAL),
        Parameter(
            name="TEST - Pressure",
            category=ParameterCategory.SPECIAL,
        ),
        Parameter(
            name="TEST - Volume",
        ),
        Parameter(
            name="TEST - Mass",
            category=ParameterCategory.NORMAL,
        ),
        Parameter(
            name="TEST - Length",
            category=ParameterCategory.NORMAL,
        ),
    ]


def generate_parameter_group_seeds(
    seeded_parameters: list[Parameter], seeded_tags: list[Tag], seeded_units: list[Unit]
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

    return [
        # Basic ParameterGroup with required fields
        ParameterGroup(
            name="TEST - General Parameters",
            type=PGType.PROPERTY,
            parameters=[
                ParameterValue(
                    id=seeded_parameters[0].id,
                    value="25.0",
                    unit=seeded_units[1],
                )
            ],
        ),
        # ParameterGroup with all fields filled out
        ParameterGroup(
            name="TEST - Batch Parameters",
            description="Parameters for batch processing",
            type=PGType.BATCH,
            security_class=SecurityClass.RESTRICTED,
            parameters=[
                ParameterValue(
                    id=seeded_parameters[1].id,
                    value="100.0",
                    unit=seeded_units[0],
                ),
                ParameterValue(
                    id=seeded_parameters[2].id,
                    value="500.0",
                    unit=seeded_units[2],
                ),
            ],
            tags=[seeded_tags[0]],
        ),
        # ParameterGroup with no tags or metadata
        ParameterGroup(
            name="TEST - Property Parameters",
            type=PGType.PROPERTY,
            parameters=[
                ParameterValue(
                    id=seeded_parameters[3].id,
                    value="75.0",
                    unit=seeded_units[0],
                ),
                ParameterValue(
                    id=seeded_parameters[4].id,
                    value="2.5",
                    unit=seeded_units[3],
                ),
            ],
        ),
    ]


def generate_inventory_seeds(
    seeded_cas: list[Cas],
    seeded_tags: list[Tag],
    seeded_companies: list[Company],
    seeded_locations: list[Location],
) -> list[InventoryItem]:
    """Generates a list of InventoryItem seed objects for testing."""
    return [
        InventoryItem(
            name="TEST - Sodium Chloride",
            description="TEST - Common salt used in various applications.",
            category=InventoryCategory.RAW_MATERIALS,
            unit_category=InventoryUnitCategory.MASS,
            security_class=SecurityClass.SHARED,
            company=seeded_companies[0],
        ),
        InventoryItem(
            name="TEST - Ethanol",
            description="TEST - A volatile, flammable liquid used in chemical synthesis.",
            category=InventoryCategory.CONSUMABLES.value,
            unit_category=InventoryUnitCategory.VOLUME.value,
            tags=seeded_tags[0:1],
            cas=[CasAmount(id=seeded_cas[1].id, min=0.98, max=1, cas_smiles=seeded_cas[1].smiles)],
            security_class=SecurityClass.SHARED,
            company=seeded_companies[1].name,  # ensure it knows to use the company object
        ),
        InventoryItem(
            name="TEST - Hydrochloric Acid",
            description="TEST - Strong acid used in various industrial processes.",
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
            storage_location=BaseEntityLink(id=seeded_storage_locations[0].id),
            initial_quantity=100.0,
            cost=50.0,
            inventory_on_hand=90.0,
            lot_number="LOT001",
            expiration_date="2025-12-31",
            manufacturer_lot_number="MLN12345",
            location=BaseEntityLink(id=seeded_locations[1].id),
            # metadata=LotMetadata(
            #     asset_tag="ASSET001",
            #     serial_number="SN123",
            #     quality_number="QN123",
            #     distributor="Distributor A",
            # ),
            notes="This is a test lot with default status.",
            external_barcode_id=str(uuid4()),
        ),
        # Lot with active status and no metadata
        Lot(
            inventory_id=seeded_inventory[0].id,
            storage_location=BaseEntityLink(id=seeded_storage_locations[1].id),
            initial_quantity=500.0,
            cost=200.0,
            inventory_on_hand=400.0,
            lot_number="LOT002",
            expiration_date="2026-01-31",
            manufacturer_lot_number="MLN67890",
            location=BaseEntityLink(id=seeded_locations[0].id),
            notes="This is an active lot with no metadata.",
            external_barcode_id=str(uuid4()),
        ),
        # Lot with quarantined status and full metadata
        Lot(
            inventory_id=seeded_inventory[1].id,
            storage_location=BaseEntityLink(id=seeded_storage_locations[1].id),
            initial_quantity=1000.0,
            cost=750.0,
            inventory_on_hand=1000.0,
            lot_number="LOT003",
            expiration_date="2024-11-30",
            manufacturer_lot_number="MLN112233",
            location=BaseEntityLink(id=seeded_locations[1].id),
            # metadata=LotMetadata(
            #     asset_tag="ASSET789",
            #     serial_number="SN789",
            #     quality_number="QN789",
            #     distributor="Distributor B",
            # ),
            notes="This lot is quarantined due to quality issues.",
            external_barcode_id=str(uuid4()),
        ),
    ]


def generate_pricing_seeds(
    seeded_inventory: list[InventoryItem], seeded_locations: list[Location]
) -> list[Pricing]:
    return [
        Pricing(
            inventory_item_id=seeded_inventory[0].id,
            company=seeded_inventory[0].company,
            location=seeded_locations[0],
            description="TEST - Pricing seed 1",
            price=42.0,
        ),
        Pricing(
            inventory_item_id=seeded_inventory[0].id,
            company=seeded_inventory[0].company,
            location=seeded_locations[1],
            description="TEST - Pricing seed 2",
            price=50.0,
        ),
        Pricing(
            inventory_item_id=seeded_inventory[1].id,
            company=seeded_inventory[2].company,
            location=seeded_locations[0],
            description="TEST - Pricing seed 3",
            price=10.50,
        ),
        Pricing(
            inventory_item_id=seeded_inventory[2].id,
            company=seeded_inventory[2].company,
            location=seeded_locations[1],
            description="TEST - Pricing seed 4",
            price=5375.97,
        ),
    ]


def generate_teams_seeds() -> list[Team]:
    return [Team(name="TEST -- Team A (SDK)"), Team(name="TEST -- Team B (SDK)")]


def generate_workflow_seeds(
    seeded_parameter_groups: list[ParameterGroup], seeded_parameters: list[Parameter]
) -> list[Workflow]:
    def _get_param_from_id(seeded_parameters, param_id):
        for x in seeded_parameters:
            if x.id == param_id:
                return x

    return [
        Workflow(
            name="TEST - Workflow 1",
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
            name="TEST - Workflow 2",
            parameter_group_setpoints=[
                ParameterGroupSetpoints(
                    parameter_group=seeded_parameter_groups[1],
                    parameter_setpoints=[
                        ParameterSetpoint(
                            parameter_id=seeded_parameter_groups[1].parameters[0].id,
                            value="25.0",
                            unit=seeded_parameter_groups[1].parameters[0].unit,
                        ),
                        ParameterSetpoint(
                            parameter=_get_param_from_id(
                                seeded_parameters, seeded_parameter_groups[1].parameters[1].id
                            ),  # Make sure setting from the parameter works
                            intervals=[
                                Interval(
                                    value="1.1", unit=seeded_parameter_groups[1].parameters[1].unit
                                ),
                                Interval(
                                    value="2.2", unit=seeded_parameter_groups[1].parameters[1].unit
                                ),
                            ],
                        ),
                    ],
                )
            ],
        ),
        Workflow(
            name="TEST - Workflow 3",
            parameter_group_setpoints=[
                ParameterGroupSetpoints(
                    parameter_group=seeded_parameter_groups[2],
                    parameter_setpoints=[
                        ParameterSetpoint(
                            parameter=_get_param_from_id(
                                seeded_parameters, seeded_parameter_groups[2].parameters[1].id
                            ),  # make sure setting from a parameter works
                            value="12.2",
                            unit=seeded_parameter_groups[2].parameters[1].unit,
                        ),
                        ParameterSetpoint(
                            parameter_id=seeded_parameter_groups[2].parameters[0].id,
                            intervals=[
                                Interval(
                                    value="1.1", unit=seeded_parameter_groups[2].parameters[0].unit
                                ),
                                Interval(
                                    value="2.2", unit=seeded_parameter_groups[2].parameters[0].unit
                                ),
                            ],
                        ),
                    ],
                )
            ],
        ),
    ]
