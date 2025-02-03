import time
import uuid
from collections.abc import Iterator
from contextlib import suppress

import jwt
import pytest

from albert import Albert
from albert.collections.worksheets import WorksheetCollection
from albert.exceptions import BadRequestError, ForbiddenError, NotFoundError
from albert.resources.btdataset import BTDataset
from albert.resources.btinsight import BTInsight
from albert.resources.btmodel import BTModel, BTModelSession
from albert.resources.cas import Cas
from albert.resources.companies import Company
from albert.resources.custom_fields import CustomField
from albert.resources.data_columns import DataColumn
from albert.resources.data_templates import DataTemplate
from albert.resources.files import FileCategory, FileInfo, FileNamespace
from albert.resources.inventory import InventoryCategory, InventoryItem
from albert.resources.lists import ListItem
from albert.resources.locations import Location
from albert.resources.parameter_groups import ParameterGroup
from albert.resources.parameters import Parameter
from albert.resources.projects import Project
from albert.resources.roles import Role
from albert.resources.sheets import Component, Sheet
from albert.resources.tags import Tag
from albert.resources.tasks import BaseTask
from albert.resources.units import Unit
from albert.resources.users import User
from albert.resources.workflows import Workflow
from albert.resources.worksheets import Worksheet
from albert.utils.client_credentials import ClientCredentials
from tests.seeding import (
    generate_cas_seeds,
    generate_company_seeds,
    generate_custom_fields,
    generate_data_column_seeds,
    generate_data_template_seeds,
    generate_inventory_seeds,
    generate_link_seeds,
    generate_list_item_seeds,
    generate_location_seeds,
    generate_lot_seeds,
    generate_note_seeds,
    generate_parameter_group_seeds,
    generate_parameter_seeds,
    generate_pricing_seeds,
    generate_project_seeds,
    generate_storage_location_seeds,
    generate_tag_seeds,
    generate_task_seeds,
    generate_teams_seeds,
    generate_unit_seeds,
    generate_workflow_seeds,
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
        retries=3,
    )


@pytest.fixture(scope="session")
def seed_prefix() -> str:
    return f"SDK-Test-{uuid.uuid4()}"


### STATIC RESOURCES -- CANNOT BE DELETED


@pytest.fixture(scope="session")
def static_image_file(client: Albert) -> FileInfo:
    try:
        r = client.files.get_by_name(name="dontpanic.jpg", namespace=FileNamespace.RESULT)
    except:
        with open("tests/data/dontpanic.jpg", "rb") as file:
            client.files.sign_and_upload_file(
                data=file,
                name="dontpanic.jpg",
                namespace=FileNamespace.RESULT,
                content_type="image/jpeg",
            )
        r = client.files.get_by_name(name="dontpanic.jpg", namespace=FileNamespace.RESULT)
    return r


@pytest.fixture(scope="session")
def static_sds_file(client: Albert) -> FileInfo:
    try:
        r = client.files.get_by_name(name="SDS_HCL.pdf", namespace=FileNamespace.RESULT)
    except:
        with open("tests/data/SDS_HCL.pdf", "rb") as file:
            client.files.sign_and_upload_file(
                data=file,
                name="SDS_HCL.pdf",
                namespace=FileNamespace.RESULT,
                content_type="application/pdf",
                category=FileCategory.SDS,
            )
        r = client.files.get_by_name(name="SDS_HCL.pdf", namespace=FileNamespace.RESULT)
    return r


@pytest.fixture(scope="session")
def static_user(client: Albert) -> User:
    # Users cannot be deleted, so we just pull the SDK client user for testing
    # Do not write to/modify this resource since it is shared across all test runs
    claims = jwt.decode(client.session._access_token, options={"verify_signature": False})
    user_id = claims["id"]
    return client.users.get_by_id(id=user_id)


@pytest.fixture(scope="session")
def static_roles(client: Albert) -> list[Role]:
    # Roles are not deleted or created. We just use the existing roles.
    return list(client.roles.list())


@pytest.fixture(scope="session")
def static_consumeable_parameter(client: Albert) -> Parameter:
    consumeables = client.parameters.list(names="Consumables")
    for c in consumeables:
        if c.name == "Consumables":
            return c


@pytest.fixture(scope="session")
def static_custom_fields(client: Albert) -> list[CustomField]:
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
    return seeded


@pytest.fixture(scope="session")
def static_lists(
    client: Albert,
    static_custom_fields: list[CustomField],
) -> list[ListItem]:
    seeded = []
    for list_item in generate_list_item_seeds(seeded_custom_fields=static_custom_fields):
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
    return seeded


@pytest.fixture(scope="session")
def static_btdataset(client: Albert) -> BTDataset:
    return client.btdatasets.get_by_id(id="DST1")


@pytest.fixture(scope="session")
def static_btinsight(client: Albert) -> BTInsight:
    return client.btinsights.get_by_id(id="INS10")


@pytest.fixture(scope="session")
def static_btmodelsession(client: Albert) -> BTModelSession:
    return client.btmodelsessions.get_by_id(id="MDS1")


@pytest.fixture(scope="session")
def static_btmodel(static_btmodelsession: BTModelSession) -> BTModel:
    return static_btmodelsession.models.get_by_id(id="MDL1")


### SEEDED RESOURCES -- CREATED ONCE PER SESSION, CAN BE DELETED


@pytest.fixture(scope="session")
def seeded_cas(client: Albert, seed_prefix: str) -> Iterator[list[Cas]]:
    seeded = []
    for cas in generate_cas_seeds(seed_prefix):
        created_cas = client.cas_numbers.create(cas=cas)
        seeded.append(created_cas)

    # Avoid race condition while it populated through DBs
    time.sleep(1.5)

    yield seeded

    for cas in seeded:
        with suppress(BadRequestError | NotFoundError):
            client.cas_numbers.delete(id=cas.id)


@pytest.fixture(scope="session")
def seeded_locations(client: Albert, seed_prefix: str) -> Iterator[list[Location]]:
    seeded = []
    for location in generate_location_seeds(seed_prefix):
        created_location = client.locations.create(location=location)
        seeded.append(created_location)

    yield seeded

    for location in seeded:
        with suppress(NotFoundError):
            client.locations.delete(id=location.id)


@pytest.fixture(scope="session")
def seeded_projects(
    client: Albert,
    seed_prefix: str,
    seeded_locations: list[Location],
) -> Iterator[list[Project]]:
    seeded = []
    for project in generate_project_seeds(
        seed_prefix=seed_prefix, seeded_locations=seeded_locations
    ):
        created_project = client.projects.create(project=project)
        seeded.append(created_project)

    yield seeded

    for project in seeded:
        with suppress(NotFoundError):
            client.projects.delete(id=project.id)


@pytest.fixture(scope="session")
def seeded_companies(client: Albert, seed_prefix: str) -> Iterator[list[Company]]:
    seeded = []
    for company in generate_company_seeds(seed_prefix):
        created_company = client.companies.create(company=company)
        seeded.append(created_company)

    yield seeded

    # ForbiddenError is raised when trying to delete a company that has InventoryItems associated with it (may be a bug. Teams discussion ongoing)
    for company in seeded:
        with suppress(NotFoundError, ForbiddenError, BadRequestError):
            client.companies.delete(id=company.id)


@pytest.fixture(scope="session")
def seeded_storage_locations(
    client: Albert,
    seeded_locations: list[Location],
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
def seeded_tags(client: Albert, seed_prefix: str) -> Iterator[list[Tag]]:
    seeded = []
    for tag in generate_tag_seeds(seed_prefix):
        created_tag = client.tags.create(tag=tag)
        seeded.append(created_tag)

    yield seeded

    for tag in seeded:
        with suppress(NotFoundError, BadRequestError):
            client.tags.delete(id=tag.id)


@pytest.fixture(scope="session")
def seeded_units(client: Albert, seed_prefix: str) -> Iterator[list[Unit]]:
    seeded = []
    for unit in generate_unit_seeds(seed_prefix):
        created_unit = client.units.create(unit=unit)
        seeded.append(created_unit)

    # Avoid race condition while it populated through search DBs
    time.sleep(1.5)

    yield seeded

    for unit in seeded:
        with suppress(NotFoundError, BadRequestError):
            client.units.delete(id=unit.id)


@pytest.fixture(scope="session")
def seeded_data_columns(
    client: Albert,
    seed_prefix: str,
    seeded_units: list[Unit],
) -> Iterator[list[DataColumn]]:
    seeded = []
    for data_column in generate_data_column_seeds(
        seed_prefix=seed_prefix,
        seeded_units=seeded_units,
    ):
        created_data_column = client.data_columns.create(data_column=data_column)
        seeded.append(created_data_column)

    # Avoid race condition while it populated through search DBs
    time.sleep(1.5)

    yield seeded

    for data_column in seeded:
        with suppress(
            NotFoundError, BadRequestError
        ):  # used on deleted InventoryItem properties are blocking. Instead of making static to accomidate the unexpected behavior, doing this instead
            client.data_columns.delete(id=data_column.id)


@pytest.fixture(scope="session")
def seeded_data_templates(
    client: Albert,
    seed_prefix: str,
    static_user: User,
    seeded_data_columns: list[DataColumn],
    seeded_units: list[Unit],
) -> Iterator[list[DataTemplate]]:
    seeded = []
    for data_template in generate_data_template_seeds(
        user=static_user,
        seed_prefix=seed_prefix,
        seeded_data_columns=seeded_data_columns,
        seeded_units=seeded_units,
    ):
        dt = client.data_templates.create(data_template=data_template)
        seeded.append(dt)

    # Avoid race condition while it populated through search DBs
    time.sleep(1.5)

    yield seeded

    for data_template in seeded:
        with suppress(NotFoundError):
            client.data_templates.delete(id=data_template.id)


@pytest.fixture(scope="session")
def seeded_worksheet(client: Albert, seeded_projects: list[Project]) -> Worksheet:
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
def seeded_sheet(seeded_worksheet: Worksheet) -> Sheet:
    for s in seeded_worksheet.sheets:
        if s.name.lower().startswith("test"):
            return s


@pytest.fixture(scope="session")
def seeded_inventory(
    client: Albert,
    seed_prefix: str,
    seeded_cas,
    seeded_tags,
    seeded_companies,
    seeded_locations,
) -> Iterator[list[InventoryItem]]:
    seeded = []
    for inventory in generate_inventory_seeds(
        seed_prefix=seed_prefix,
        seeded_cas=seeded_cas,
        seeded_tags=seeded_tags,
        seeded_companies=seeded_companies,
        seeded_locations=seeded_locations,
    ):
        created_inventory = client.inventory.create(inventory_item=inventory)
        seeded.append(created_inventory)
    time.sleep(1.5)
    yield seeded
    for inventory in seeded:
        # If the inv has been used in a formulation, it cannot be deleted and will give a BadRequestError
        with suppress(NotFoundError, BadRequestError):
            client.inventory.delete(id=inventory.id)


@pytest.fixture(scope="session")
def seeded_parameters(client: Albert, seed_prefix: str) -> Iterator[list[Parameter]]:
    seeded = []
    for parameter in generate_parameter_seeds(seed_prefix):
        created_parameter = client.parameters.create(parameter=parameter)
        # Extra get_by_id is required to populate the category field on parameter
        seeded.append(client.parameters.get_by_id(id=created_parameter.id))
    yield seeded
    for parameter in seeded:
        with suppress(NotFoundError):
            client.parameters.delete(id=parameter.id)


@pytest.fixture(scope="session")
def seeded_parameter_groups(
    client: Albert,
    seed_prefix: str,
    seeded_parameters,
    seeded_tags,
    seeded_units,
    static_consumeable_parameter: Parameter,
) -> Iterator[list[ParameterGroup]]:
    seeded = []
    for parameter_group in generate_parameter_group_seeds(
        seed_prefix=seed_prefix,
        seeded_parameters=seeded_parameters,
        seeded_tags=seeded_tags,
        seeded_units=seeded_units,
        static_consumeable_parameter=static_consumeable_parameter,
    ):
        created_parameter_group = client.parameter_groups.create(parameter_group=parameter_group)
        seeded.append(created_parameter_group)

    # Avoid race condition while it populates through DBs
    time.sleep(1.5)

    yield seeded

    for parameter_group in seeded:
        with suppress(NotFoundError):
            client.parameter_groups.delete(id=parameter_group.id)


# PUT on lots is currently bugged. Teams discussion ongoing
@pytest.fixture(scope="session")
def seeded_lots(
    client: Albert,
    seeded_inventory,
    seeded_storage_locations,
    seeded_locations,
):
    seeded = []
    all_lots = generate_lot_seeds(
        seeded_inventory=seeded_inventory,
        seeded_storage_locations=seeded_storage_locations,
        seeded_locations=seeded_locations,
    )
    seeded = client.lots.create(lots=all_lots)
    yield seeded
    for lot in seeded:
        with suppress(NotFoundError):
            client.lots.delete(id=lot.id)


@pytest.fixture(scope="session")
def seeded_pricings(client: Albert, seed_prefix: str, seeded_inventory, seeded_locations):
    seeded = []
    for p in generate_pricing_seeds(seed_prefix, seeded_inventory, seeded_locations):
        seeded.append(client.pricings.create(pricing=p))
    yield seeded
    for p in seeded:
        with suppress(NotFoundError):
            client.pricings.delete(id=p.id)


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


@pytest.fixture(scope="session")
def seeded_workflows(
    client: Albert,
    seed_prefix: str,
    seeded_parameter_groups: list[ParameterGroup],
    seeded_parameters: list[Parameter],
    static_consumeable_parameter: Parameter,
    seeded_inventory: list[InventoryItem],
) -> list[Workflow]:
    all_workflows = generate_workflow_seeds(
        seed_prefix=seed_prefix,
        seeded_parameter_groups=seeded_parameter_groups,
        seeded_parameters=seeded_parameters,
        static_consumeable_parameter=static_consumeable_parameter,
        seeded_inventory=seeded_inventory,
    )

    return client.workflows.create(workflows=all_workflows)


@pytest.fixture(scope="session")
def seeded_products(
    client: Albert,
    seed_prefix: str,
    seeded_sheet: Sheet,
    seeded_inventory: list[InventoryItem],
) -> list[InventoryItem]:
    product_name_prefix = f"{seed_prefix} - My cool formulation"
    products = []

    components = [
        Component(inventory_item=seeded_inventory[0], amount=66),
        Component(inventory_item=seeded_inventory[1], amount=34),
    ]
    for n in range(4):
        products.append(
            seeded_sheet.add_formulation(
                formulation_name=f"{product_name_prefix} {str(n)}",
                components=components,
            )
        )
    return [
        x
        for x in client.inventory.list(
            category=InventoryCategory.FORMULAS,
            text=product_name_prefix,
        )
        if x.name is not None and x.name.startswith(product_name_prefix)
    ]


@pytest.fixture(scope="session")
def seeded_tasks(
    client: Albert,
    seed_prefix: str,
    static_user: User,
    seeded_inventory,
    seeded_lots,
    seeded_projects,
    seeded_locations,
    seeded_data_templates,
    seeded_workflows,
    seeded_products,
):
    seeded = []
    all_tasks = generate_task_seeds(
        seed_prefix=seed_prefix,
        user=static_user,
        seeded_inventory=seeded_inventory,
        seeded_lots=seeded_lots,
        seeded_projects=seeded_projects,
        seeded_locations=seeded_locations,
        seeded_data_templates=seeded_data_templates,
        seeded_workflows=seeded_workflows,
        seeded_products=seeded_products,
    )
    for t in all_tasks:
        seeded.append(client.tasks.create(task=t))
    yield seeded
    # workflows cannot be deleted
    for t in seeded:
        with suppress(NotFoundError, BadRequestError):
            client.tasks.delete(id=t.id)


@pytest.fixture(scope="session")
def seeded_notes(
    client: Albert,
    seeded_tasks: list[BaseTask],
    seeded_inventory: list[InventoryItem],
    seed_prefix: str,
):
    seeded = []
    for note in generate_note_seeds(
        seeded_tasks=seeded_tasks, seeded_inventory=seeded_inventory, seed_prefix=seed_prefix
    ):
        seeded.append(client.notes.create(note=note))
    yield seeded
    for note in seeded:
        with suppress(NotFoundError):
            client.notes.delete(id=note.id)


@pytest.fixture(scope="session")
def seeded_links(client: Albert, seeded_tasks: list[BaseTask]):
    seeded = client.links.create(links=generate_link_seeds(seeded_tasks=seeded_tasks))
    yield seeded
    for link in seeded:
        with suppress(NotFoundError):
            client.links.delete(id=link.id)
