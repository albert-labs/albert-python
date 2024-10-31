import time
from collections.abc import Iterator
from contextlib import suppress

import pytest

from albert import Albert
from albert.collections.worksheets import WorksheetCollection
from albert.resources.base import Status
from albert.resources.cas import Cas
from albert.resources.companies import Company
from albert.resources.custom_fields import CustomField
from albert.resources.data_columns import DataColumn
from albert.resources.data_templates import DataTemplate
from albert.resources.inventory import InventoryItem
from albert.resources.lists import ListItem
from albert.resources.locations import Location
from albert.resources.parameters import Parameter
from albert.resources.projects import Project
from albert.resources.roles import Role
from albert.resources.sheets import Sheet
from albert.resources.tags import Tag
from albert.resources.units import Unit
from albert.resources.users import User
from albert.resources.worksheets import Worksheet
from albert.utils.client_credentials import ClientCredentials
from albert.utils.exceptions import BadRequestError, ForbiddenError, NotFoundError
from tests.seeding import (
    generate_cas_seeds,
    generate_company_seeds,
    generate_custom_fields,
    generate_data_column_seeds,
    generate_data_template_seeds,
    generate_inventory_seeds,
    generate_list_item_seeds,
    generate_location_seeds,
    generate_lot_seeds,
    generate_parameter_group_seeds,
    generate_parameter_seeds,
    generate_pricing_seeds,
    generate_project_seeds,
    generate_storage_location_seeds,
    generate_tag_seeds,
    generate_teams_seeds,
    generate_unit_seeds,
    generate_user_seeds,
)


@pytest.fixture(scope="session")
def client() -> Albert:
    credentials = ClientCredentials.from_env(
        client_id_env="ALBERT_CLIENT_ID_SDK",
        client_secret_env="ALBERT_CLIENT_SECRET_SDK",
    )
    return Albert(
        base_url="https://app.albertinvent.com",
        client_credentials=credentials,
    )


@pytest.fixture(scope="session")
def seeded_custom_fields(client: Albert):
    seeded = []
    for cf in generate_custom_fields():
        try:
            registered_cf = client.custom_fields.create(custom_field=cf)
        except BadRequestError as e:
            # If it's already registered, this will raise a BadRequestError
            registered_cf = client.custom_fields.get_by_name(name=cf.name)
            if registered_cf is None:  # If it was something else, raise the error
                raise e
        seeded.append(registered_cf)
    yield seeded

    # Custom Fields cannot be deleted


@pytest.fixture(scope="session")
def seeded_projects(client: Albert, seeded_locations) -> Iterator[list[Project]]:
    # Seed the projects using seeded locations

    seeded = []

    for project in generate_project_seeds(seeded_locations=seeded_locations):
        existing = client.projects.list()
        for m in existing:
            if m.description.lower() == project.description.lower():
                client.projects.delete(project_id=m.id)
        created_project = client.projects.create(project=project)
        seeded.append(created_project)

    yield seeded  # Provide the seeded projects to the test

    # Teardown - delete the seeded projects after the test
    for project in seeded:
        with suppress(NotFoundError):
            client.projects.delete(project_id=project.id)


@pytest.fixture(scope="session")
def seeded_cas(client: Albert) -> Iterator[list[Cas]]:
    # Seed the CAS
    seeded = []
    for cas in generate_cas_seeds():
        created_cas = client.cas_numbers.create(cas=cas)
        seeded.append(created_cas)
    time.sleep(1.5)  # avoid race condition while it populated through DBs
    yield seeded  # Provide the seeded CAS to the test

    # Teardown - delete the seeded CAS after the test
    for cas in seeded:
        with suppress(BadRequestError | NotFoundError):
            client.cas_numbers.delete(cas_id=cas.id)


@pytest.fixture(scope="session")
def seeded_companies(client: Albert) -> Iterator[list[Company]]:
    # Seed the companies
    seeded = []
    for company in generate_company_seeds():
        created_company = client.companies.create(company=company)
        seeded.append(created_company)

    yield seeded  # Provide the seeded companies to the test

    # Teardown - delete the seeded companies after the test
    # ForbiddenError is raised when trying to delete a company that has InventoryItems associated with it (may be a bug. Teams discussion ongoing)
    for company in seeded:
        with suppress(NotFoundError, ForbiddenError, BadRequestError):
            client.companies.delete(id=company.id)


@pytest.fixture(scope="session")
def seeded_locations(client: Albert) -> Iterator[list[Location]]:
    # Seed the Locations
    seeded = []
    for location in generate_location_seeds():
        created_location = client.locations.create(location=location)
        seeded.append(created_location)

    yield seeded  # Provide the seeded Locations to the test

    # Teardown - delete the seeded Locations after the test
    for location in seeded:
        with suppress(NotFoundError):
            client.locations.delete(location_id=location.id)


@pytest.fixture(scope="session")
def seeded_storage_locations(
    client: Albert, seeded_locations: list[Location]
) -> Iterator[list[Location]]:
    seeded = []
    for storage_location in generate_storage_location_seeds(seeded_locations=seeded_locations):
        created_location = client.storage_locations.create(storage_location=storage_location)
        seeded.append(created_location)
    yield seeded

    for storage_location in seeded:
        with suppress(NotFoundError):
            client.storage_locations.delete(id=storage_location.id)


@pytest.fixture(scope="session")
def seeded_lists(
    client: Albert, seeded_custom_fields: list[CustomField]
) -> Iterator[list[ListItem]]:
    seeded = []
    # Seed the lists
    for list_item in generate_list_item_seeds(seeded_custom_fields=seeded_custom_fields):
        try:
            created_list = client.lists.create(list_item=list_item)
        except BadRequestError as e:
            # If it's already registered, this will raise a BadRequestError
            created_list = client.lists.get_matching_item(
                name=list_item.name, list_type=list_item.list_type
            )
            if created_list is None:
                raise e
        seeded.append(created_list)

    yield seeded
    # NOTE: There is NO delete method for lists. This is because the list Items cannot be deleted in the Albert API.


@pytest.fixture(scope="session")
def seeded_tags(client: Albert) -> Iterator[list[Tag]]:
    # Seed the tags
    seeded = []
    for tag in generate_tag_seeds():
        created_tag = client.tags.create(tag=tag)
        seeded.append(created_tag)

    yield seeded  # Provide the seeded tags to the test

    # Teardown - delete the seeded tags after the test
    for tag in seeded:
        with suppress(NotFoundError, BadRequestError):
            client.tags.delete(tag_id=tag.id)


@pytest.fixture(scope="session")
def seeded_units(client: Albert) -> Iterator[list[Unit]]:
    # Seed the units
    seeded = []
    for unit in generate_unit_seeds():
        created_unit = client.units.create(unit=unit)
        seeded.append(created_unit)
    time.sleep(1.5)  # avoid race condition while it populated through DBs
    yield seeded  # Provide the seeded units to the test

    # Teardown - delete the seeded units after the test
    for unit in seeded:
        with suppress(NotFoundError, BadRequestError):
            client.units.delete(unit_id=unit.id)


@pytest.fixture(scope="session")
def seeded_data_columns(client: Albert, seeded_units: list[Unit]) -> Iterator[list[DataColumn]]:
    # Seed the data columns
    seeded = []
    for data_column in generate_data_column_seeds(seeded_units=seeded_units):
        created_data_column = client.data_columns.get_by_name(name=data_column.name)
        if created_data_column is None:
            created_data_column = client.data_columns.create(data_column=data_column)
        seeded.append(created_data_column)
    time.sleep(1.5)
    yield seeded  # Provide the seeded data columns to the test

    # tearDown - delete the seeded data columns after the test
    for data_column in seeded:
        with suppress(NotFoundError):
            client.data_columns.delete(data_column_id=data_column.id)


@pytest.fixture(scope="session")
def seeded_roles(client: Albert) -> Iterator[list[Role]]:
    # Roles are not deleted or created. We just use the existing roles.
    existing = []
    for role in client.roles.list():
        existing.append(role)

    yield existing  # Provide the seeded units to the test


@pytest.fixture(scope="session")
def seeded_users(client: Albert, seeded_roles, seeded_locations) -> Iterator[list[User]]:
    seeded = []
    # Here, seeded_roles and seeded_locations will already be lists from the respective fixtures

    for user in generate_user_seeds(seeded_roles=seeded_roles, seeded_locations=seeded_locations):
        matches = client.users.list(text=user.name)
        found = False
        for m in matches:
            if m.name == user.name:
                created_user = m
                created_user.status = Status.ACTIVE.value
                client.users.update(updated_object=created_user)
                found = True
                break
        if not found:
            created_user = client.users.create(user=user)
        seeded.append(created_user)
    time.sleep(1.5)  # avoid race condition while it populates through DBs
    yield seeded  # Provide the seeded users to the test

    # Teardown - archive/set inactive
    for user in seeded:
        user.status = Status.INACTIVE.value
        client.users.update(updated_object=user)


@pytest.fixture(scope="session")
def seeded_data_templates(
    client: Albert,
    seeded_data_columns: list[DataColumn],
    seeded_users: list[User],
    seeded_units: list[Unit],
) -> Iterator[list[DataTemplate]]:
    seeded = []
    for data_template in generate_data_template_seeds(
        seeded_data_columns=seeded_data_columns,
        seeded_units=seeded_units,
        seeded_users=seeded_users,
    ):
        dt = client.data_templates.get_by_name(name=data_template.name)
        if dt is None:
            dt = client.data_templates.create(data_template=data_template)
        seeded.append(dt)
    yield seeded
    for data_template in seeded:
        with suppress(NotFoundError):
            client.data_templates.delete(data_template_id=data_template.id)


# Move to conftest.py in a bit
@pytest.fixture(scope="session")
def worksheet(client: Albert, seeded_projects: list[Project]) -> Worksheet:
    collection = WorksheetCollection(session=client.session)
    try:
        wksht = collection.get_by_project_id(project_id=seeded_projects[0].id)
    except NotFoundError:
        wksht = collection.setup_worksheet(project_id=seeded_projects[0].id)
    if wksht.sheets is None or wksht.sheets == []:
        wksht = collection.setup_new_worksheet_blank(
            project_id=seeded_projects[0].id, sheet_name="test"
        )
    else:
        for s in wksht.sheets:
            if not s.name.lower().startswith("test"):
                s.rename(new_name=f"test {s.name}")
                return collection.get_by_project_id(project_id=seeded_projects[0].id)
    return wksht


@pytest.fixture(scope="session")
def sheet(worksheet: Worksheet) -> Sheet:
    for s in worksheet.sheets:
        if s.name.lower().startswith("test"):
            return s


@pytest.fixture(scope="session")
def seeded_inventory(
    client: Albert, seeded_cas, seeded_tags, seeded_companies, seeded_locations
) -> Iterator[list[InventoryItem]]:
    seeded = []
    for inventory in generate_inventory_seeds(
        seeded_cas=seeded_cas,
        seeded_tags=seeded_tags,
        seeded_companies=seeded_companies,
        seeded_locations=seeded_locations,
    ):
        created_inventory = client.inventory.create(inventory_item=inventory)
        seeded.append(created_inventory)
    yield seeded
    for inventory in seeded:
        # If the inv has been used in a formulation, it cannot be deleted and will give a BadRequestError
        with suppress(NotFoundError, BadRequestError):
            client.inventory.delete(inventory_id=inventory.id)


@pytest.fixture(scope="session")
def seeded_parameters(client: Albert) -> Iterator[list[Parameter]]:
    seeded = []
    for parameter in generate_parameter_seeds():
        created_parameter = client.parameters.create(parameter=parameter)
        seeded.append(created_parameter)
    yield seeded
    for parameter in seeded:
        with suppress(NotFoundError):
            client.parameters.delete(id=parameter.id)


@pytest.fixture(scope="session")
def seeded_parameter_groups(
    client: Albert, seeded_parameters, seeded_tags, seeded_units
) -> Iterator[list[Parameter]]:
    seeded = []
    for parameter_group in generate_parameter_group_seeds(
        seeded_parameters=seeded_parameters, seeded_tags=seeded_tags, seeded_units=seeded_units
    ):
        created_parameter_group = client.parameter_groups.create(parameter_group=parameter_group)
        seeded.append(created_parameter_group)
        time.sleep(1.5)  # avoid race condition while it populates through DBs

    yield seeded
    for parameter_group in seeded:
        with suppress(NotFoundError):
            client.parameter_groups.delete(id=parameter_group.id)


# PUT on lots is currently bugged. Teams discussion ongoing
@pytest.fixture(scope="session")
def seeded_lots(client: Albert, seeded_inventory, seeded_storage_locations, seeded_locations):
    seeded = []
    all_lots = generate_lot_seeds(
        seeded_inventory=seeded_inventory,
        seeded_storage_locations=seeded_storage_locations,
        seeded_locations=seeded_locations,
    )
    seeded = client.lots.create(lots=all_lots)
    # seeded.append(created_lot)
    yield seeded
    for lot in seeded:
        with suppress(NotFoundError):
            client.lots.delete(lot_id=lot.id)


@pytest.fixture(scope="session")
def seeded_pricings(client: Albert, seeded_inventory, seeded_locations):
    seeded = []
    all_pricing = generate_pricing_seeds(
        seeded_inventory=seeded_inventory,
        seeded_locations=seeded_locations,
    )
    for p in all_pricing:
        seeded.append(client.pricings.create(pricing=p))
    yield seeded
    for p in seeded:
        with suppress(NotFoundError):
            client.pricings.delete(pricing_id=p.id)


@pytest.fixture(scope="session")
def seeded_teams(client: Albert):
    seeded = []  # init list
    all_teams = generate_teams_seeds()  # get list of teams from "seeding.py"
    for t in all_teams:
        seeded.append(client.teams.create(team=t))  # create all teams -> "setup"
    yield seeded
    for t in seeded:
        with suppress(NotFoundError):
            client.teams.delete(team_id=t.id)  # delete all teams -> "cleanup"
