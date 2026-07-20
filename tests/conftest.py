import time
import uuid
from collections.abc import AsyncGenerator, Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from pathlib import Path

import pytest
import pytest_asyncio

from albert import Albert, AlbertClientCredentials, AsyncAlbert
from albert.collections.worksheets import WorksheetCollection
from albert.core.shared.enums import Status
from albert.exceptions import (
    AlbertServerError,
    BadRequestError,
    ForbiddenError,
    NotFoundError,
)
from albert.resources.attachments import Attachment
from albert.resources.btdataset import BTDataset
from albert.resources.btinsight import BTInsight
from albert.resources.btmodel import BTModel, BTModelSession
from albert.resources.cas import Cas
from albert.resources.chats import (
    ChatComponentType,
    ChatFolder,
    ChatMessage,
    ChatRole,
    ChatSession,
    ChatUserType,
)
from albert.resources.companies import Company
from albert.resources.custom_fields import CustomField
from albert.resources.custom_templates import CustomTemplate, GeneralData, TemplateCategory
from albert.resources.data_columns import DataColumn
from albert.resources.data_templates import DataTemplate
from albert.resources.entity_types import EntityType
from albert.resources.files import FileCategory, FileInfo, FileNamespace
from albert.resources.inventory import InventoryCategory, InventoryItem
from albert.resources.label_templates import LabelTemplate, LabelTemplateType
from albert.resources.lists import ListItem
from albert.resources.locations import Location
from albert.resources.lots import Lot
from albert.resources.notes import Note
from albert.resources.parameter_groups import ParameterGroup
from albert.resources.parameters import Parameter
from albert.resources.projects import Project
from albert.resources.reports import FullAnalyticalReport
from albert.resources.roles import Role
from albert.resources.sheets import Component, Sheet
from albert.resources.smart_datasets import SmartDataset, SmartDatasetBuildState
from albert.resources.storage_locations import StorageLocation
from albert.resources.tags import Tag
from albert.resources.targets import Target
from albert.resources.tasks import BaseTask
from albert.resources.teams import Team, TeamMember
from albert.resources.units import Unit
from albert.resources.users import User
from albert.resources.workflows import Workflow
from albert.resources.worksheets import Worksheet
from tests.seeding import (
    generate_btdataset_seed,
    generate_btinsight_seed,
    generate_btmodel_seed,
    generate_btmodelsession_seed,
    generate_cas_seeds,
    generate_company_seeds,
    generate_custom_fields,
    generate_data_column_seeds,
    generate_data_template_seeds,
    generate_entity_custom_fields,
    generate_entity_type_seeds,
    generate_inventory_seeds,
    generate_link_seeds,
    generate_list_item_seeds,
    generate_location_seeds,
    generate_lot_seeds,
    generate_note_seeds,
    generate_notebook_block_seeds,
    generate_notebook_seeds,
    generate_parameter_group_seeds,
    generate_parameter_seeds,
    generate_pricing_seeds,
    generate_project_seeds,
    generate_report_seeds,
    generate_smart_dataset_seed,
    generate_storage_location_seeds,
    generate_tag_seeds,
    generate_target_seeds,
    generate_task_seeds,
    generate_unit_seeds,
    generate_workflow_seeds,
)
from tests.utils.fake_session import FakeAlbertSession


def _pmap(fn: Callable, items) -> list:
    """Run independent seeding API calls concurrently, preserving input order.

    Retries once on 5xx: the session's urllib3 retry only covers idempotent methods,
    so seeding POSTs otherwise fail on a single transient gateway error.
    """

    def _one(item):
        try:
            return fn(item)
        except AlbertServerError:
            time.sleep(2.0)
            return fn(item)

    items = list(items)
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(items)))) as ex:
        return list(ex.map(_one, items))


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    """Report slow fixture setups so seeding regressions stay visible."""
    start = time.monotonic()
    yield
    elapsed = time.monotonic() - start
    if elapsed > 5:
        print(f"[slow fixture] {fixturedef.argname}: {elapsed:.1f}s", flush=True)


def _get_or_register(create_fn: Callable, get_fn: Callable, *, timeout: float = 10.0):
    """Create a shared (non-prefixed) entity, falling back to fetching it.

    Concurrent xdist workers register the same static entities; the backend may answer
    the loser with a 400 (already exists) or buckle with a 5xx. Either way the entity
    usually exists, so poll the getter before giving up.
    """
    try:
        return create_fn()
    except (BadRequestError, AlbertServerError) as e:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with suppress(Exception):
                found = get_fn()
                if found is not None:
                    return found
            time.sleep(0.5)
        raise e


def _delete_all(delete_fn: Callable, items, *suppressed: type[Exception]) -> None:
    """Delete seeded entities concurrently, suppressing the given exceptions."""

    def _one(item):
        with suppress(*suppressed):
            delete_fn(item)

    _pmap(_one, items)


@pytest.fixture(scope="session")
def client() -> Albert:
    credentials = AlbertClientCredentials.from_env(
        client_id_env="ALBERT_CLIENT_ID_SDK",
        client_secret_env="ALBERT_CLIENT_SECRET_SDK",
        base_url_env="ALBERT_BASE_URL",
    )
    return Albert(
        auth_manager=credentials,
        retries=3,
    )


@pytest_asyncio.fixture(scope="session")
async def async_client() -> AsyncGenerator[AsyncAlbert, None]:
    credentials = AlbertClientCredentials.from_env(
        client_id_env="ALBERT_CLIENT_ID_SDK",
        client_secret_env="ALBERT_CLIENT_SECRET_SDK",
        base_url_env="ALBERT_BASE_URL",
    )
    client = AsyncAlbert(
        auth_manager=credentials,
    )
    yield client
    await client.aclose()


@pytest.fixture
def fake_client() -> Albert:
    """Fixture to provide a fake session for testing."""
    client = Albert(
        base_url="https://fake.albertinvent.com", token="fake-token", session=FakeAlbertSession()
    )
    return client


@pytest.fixture(scope="session")
def seed_prefix() -> str:
    return f"SDK-Test-{uuid.uuid4()}"


### STATIC RESOURCES -- CANNOT BE DELETED


@pytest.fixture(scope="session")
def static_user(client: Albert) -> User:
    # Users cannot be deleted, so we just pull the SDK Bot user for testing
    # Do not write to/modify this resource since it is shared across all test runs
    return client.users.get_current_user()


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
def static_roles(client: Albert) -> list[Role]:
    # Roles are not deleted or created. We just use the existing roles.
    return list(client.roles.get_all())


@pytest.fixture(scope="session")
def static_consumeable_parameter(client: Albert) -> Parameter:
    consumeables = client.parameters.get_all(names="Consumables")
    for c in consumeables:
        if c.name == "Consumables":
            return c


def _register_custom_field(client: Albert, cf: CustomField) -> CustomField:
    return _get_or_register(
        lambda: client.custom_fields.create(custom_field=cf),
        lambda: client.custom_fields.get_by_name(name=cf.name, service=cf.service),
    )


@pytest.fixture(scope="session")
def static_custom_fields(client: Albert) -> list[CustomField]:
    # Sequential on purpose: shared names race across xdist workers
    return [_register_custom_field(client, cf) for cf in generate_custom_fields()]


@pytest.fixture(scope="session")
def static_entity_custom_fields(client: Albert) -> list[CustomField]:
    """Custom fields associated with an entity type."""
    return [_register_custom_field(client, cf) for cf in generate_entity_custom_fields()]


@pytest.fixture(scope="session")
def static_lists(
    client: Albert,
    static_custom_fields: list[CustomField],
) -> list[ListItem]:
    # Sequential on purpose: shared names race across xdist workers
    return [
        _get_or_register(
            lambda li=list_item: client.lists.create(list_item=li),
            lambda li=list_item: client.lists.get_matching_item(
                name=li.name, list_type=li.list_type
            ),
        )
        for list_item in generate_list_item_seeds(seeded_custom_fields=static_custom_fields)
    ]


### TEAM FIXTURES


@pytest.fixture(scope="session")
def second_user(client: Albert, static_user: User) -> User:
    """Get a second active user distinct from the static SDK bot user."""
    for user in client.users.search(max_items=50):
        hydrated = client.users.get_by_id(id=user.id)
        if hydrated.id != static_user.id and hydrated.status == Status.ACTIVE:
            return hydrated
    pytest.skip("No second active user available for team tests")


@pytest.fixture(scope="session")
def seeded_team(client: Albert, seed_prefix: str, static_user: User) -> Iterator[Team]:
    """Create a team with a member for testing and clean up after."""
    team = client.teams.create(
        name=f"{seed_prefix}-team-seeded",
        members=[TeamMember(id=static_user.id, role="TeamOwner")],
    )
    yield team
    with suppress(Exception):
        client.teams.delete(id=team.id)


### SEEDED RESOURCES -- CREATED ONCE PER SESSION, CAN BE DELETED


@pytest.fixture(scope="session")
def seeded_cas(
    client: Albert,
    seed_prefix: str,
    static_custom_fields: list[CustomField],
    static_lists: list[ListItem],
) -> Iterator[list[Cas]]:
    def _seed(cas: Cas) -> Cas | None:
        with suppress(BadRequestError):
            return client.cas_numbers.get_or_create(cas=cas)

    results = _pmap(_seed, generate_cas_seeds(seed_prefix, static_custom_fields, static_lists))
    seeded = [cas for cas in results if cas is not None]

    # Avoid race condition while it populated through DBs
    time.sleep(3)

    yield seeded

    _delete_all(
        lambda cas: client.cas_numbers.delete(id=cas.id), seeded, BadRequestError, NotFoundError
    )


@pytest.fixture(scope="session")
def seeded_locations(client: Albert, seed_prefix: str) -> Iterator[list[Location]]:
    seeded = _pmap(
        lambda location: client.locations.get_or_create(location=location),
        generate_location_seeds(seed_prefix),
    )

    yield seeded

    _delete_all(lambda location: client.locations.delete(id=location.id), seeded, NotFoundError)


@pytest.fixture(scope="session")
def seeded_projects(
    client: Albert,
    seed_prefix: str,
    seeded_locations: list[Location],
    static_custom_fields: list[CustomField],
    static_lists: list[ListItem],
) -> Iterator[list[Project]]:
    seeded = _pmap(
        lambda project: client.projects.create(project=project),
        generate_project_seeds(
            seed_prefix=seed_prefix,
            seeded_locations=seeded_locations,
            static_custom_fields=static_custom_fields,
            static_lists=static_lists,
        ),
    )

    yield seeded

    _delete_all(lambda project: client.projects.delete(id=project.id), seeded, NotFoundError)


@pytest.fixture(scope="session")
def seeded_project_document(
    client: Albert,
    seeded_projects: list[Project],
) -> Iterator[Attachment]:
    attachment = client.attachments.upload_and_attach_document_to_project(
        project_id=seeded_projects[0].id,
        file_path=Path("tests/data/dontpanic.jpg"),
    )
    # Allow time for search index to update
    time.sleep(3)

    yield attachment

    with suppress(NotFoundError):
        client.attachments.delete(id=attachment.id)


@pytest.fixture(scope="session")
def seeded_companies(client: Albert, seed_prefix: str) -> Iterator[list[Company]]:
    seeded = _pmap(
        lambda company: client.companies.get_or_create(company=company),
        generate_company_seeds(seed_prefix),
    )

    yield seeded

    # ForbiddenError is raised when trying to delete a company that has InventoryItems associated with it (may be a bug. Teams discussion ongoing)
    _delete_all(
        lambda company: client.companies.delete(id=company.id),
        seeded,
        NotFoundError,
        ForbiddenError,
        BadRequestError,
    )


@pytest.fixture(scope="session")
def seeded_storage_locations(
    client: Albert,
    seeded_locations: list[Location],
) -> Iterator[list[StorageLocation]]:
    seeded = _pmap(
        lambda storage_location: client.storage_locations.get_or_create(
            storage_location=storage_location
        ),
        generate_storage_location_seeds(seeded_locations=seeded_locations),
    )

    yield seeded

    _delete_all(
        lambda storage_location: client.storage_locations.delete(id=storage_location.id),
        seeded,
        NotFoundError,
    )


@pytest.fixture(scope="session")
def seeded_tags(client: Albert, seed_prefix: str) -> Iterator[list[Tag]]:
    seeded = _pmap(
        lambda tag: client.tags.get_or_create(tag=tag),
        generate_tag_seeds(seed_prefix),
    )

    yield seeded

    _delete_all(lambda tag: client.tags.delete(id=tag.id), seeded, NotFoundError, BadRequestError)


@pytest.fixture(scope="session")
def seeded_custom_templates(
    client: Albert,
    seed_prefix: str,
) -> Iterator[list[CustomTemplate]]:
    seeded: list[CustomTemplate] = []
    name = f"{seed_prefix}-general"
    data = GeneralData(name=name)
    custom_template = CustomTemplate(
        name=name,
        data=data,
        category=TemplateCategory.GENERAL,
    )
    created_templates = client.custom_templates.create(custom_template=custom_template)
    seeded.extend(created_templates)

    # Avoid race condition while it populated through search DBs
    time.sleep(1.5)

    yield seeded

    for template in seeded:
        with suppress(NotFoundError):
            client.custom_templates.delete(id=template.id)


@pytest.fixture(scope="session")
def seeded_label_templates(
    client: Albert,
    seed_prefix: str,
) -> Iterator[list[LabelTemplate]]:
    template = LabelTemplate(
        name=f"{seed_prefix}-inventory-label",
        type=LabelTemplateType.INVENTORY,
        template_file=f"{seed_prefix}-inventory-label.html",
        description="SDK test inventory label template",
        metadata={"width": "4in", "height": "2in"},
    )
    template_html = (
        "<html><head>"
        '<meta charset="UTF-8">'
        '<!--metadata:{"width": "4in", "height": "2in",'
        ' "margin": {"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"}}-->'
        "<style>body { font-family: Arial, sans-serif; overflow: hidden; }</style>"
        "</head><body>"
        "{{#labels}}"
        "<div><h3>{{info.inventoryName}}</h3>"
        "<p>{{info.albertId}} | {{info.expirationDate}}</p>"
        '<img src="{{{info.lotNumber}}}" width="100" height="40" />'
        '<img src="{{{info.lotNumberQrCode}}}" width="80" height="80" />'
        "</div>"
        "{{/labels}}"
        "</body></html>"
    )
    created = client.label_templates.create(
        label_template=template,
        template_html=template_html,
    )
    seeded = [created]

    yield seeded

    for label_template in seeded:
        with suppress(NotFoundError):
            client.label_templates.delete(id=label_template.id)


@pytest.fixture(scope="session")
def seeded_units(client: Albert, seed_prefix: str) -> Iterator[list[Unit]]:
    seeded = _pmap(
        lambda unit: client.units.get_or_create(unit=unit),
        generate_unit_seeds(seed_prefix),
    )

    # Avoid race condition while it populated through search DBs
    time.sleep(1.5)

    yield seeded

    _delete_all(
        lambda unit: client.units.delete(id=unit.id), seeded, NotFoundError, BadRequestError
    )


@pytest.fixture(scope="session")
def seeded_data_columns(
    client: Albert,
    seed_prefix: str,
    seeded_units: list[Unit],
) -> Iterator[list[DataColumn]]:
    seeded = _pmap(
        lambda data_column: client.data_columns.create(data_column=data_column),
        generate_data_column_seeds(seed_prefix=seed_prefix, seeded_units=seeded_units),
    )

    # Avoid race condition while it populated through search DBs
    time.sleep(1.5)

    yield seeded

    # used on deleted InventoryItem properties are blocking. Instead of making static to accomidate the unexpected behavior, doing this instead
    _delete_all(
        lambda data_column: client.data_columns.delete(id=data_column.id),
        seeded,
        NotFoundError,
        BadRequestError,
    )


@pytest.fixture(scope="session")
def seeded_data_templates(
    client: Albert,
    seed_prefix: str,
    static_user: User,
    seeded_data_columns: list[DataColumn],
    seeded_units: list[Unit],
    seeded_tags: list[Tag],
    seeded_parameters: list[Parameter],
    static_custom_fields: list[CustomField],
    static_lists: list[ListItem],
) -> Iterator[list[DataTemplate]]:
    seeded = _pmap(
        lambda data_template: client.data_templates.create(data_template=data_template),
        generate_data_template_seeds(
            user=static_user,
            seed_prefix=seed_prefix,
            seeded_data_columns=seeded_data_columns,
            seeded_units=seeded_units,
            seeded_tags=seeded_tags,
            seeded_parameters=seeded_parameters,
            static_custom_fields=static_custom_fields,
            static_lists=static_lists,
        ),
    )

    # Avoid race condition while it populated through search DBs
    time.sleep(1.5)

    yield seeded

    _delete_all(
        lambda data_template: client.data_templates.delete(id=data_template.id),
        seeded,
        NotFoundError,
    )


@pytest.fixture(scope="session")
def seeded_worksheet(client: Albert, seeded_projects: list[Project]) -> Worksheet:
    collection = WorksheetCollection(session=client.session)
    try:
        wksht = collection.get_by_project_id(project_id=seeded_projects[0].id)
    except NotFoundError:
        wksht = collection.setup_worksheet(project_id=seeded_projects[0].id)
    if not wksht.sheets:
        wksht = collection.add_sheet(project_id=seeded_projects[0].id, sheet_name="test")
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
    seeded = _pmap(
        lambda inventory: client.inventory.create(inventory_item=inventory),
        generate_inventory_seeds(
            seed_prefix=seed_prefix,
            seeded_cas=seeded_cas,
            seeded_tags=seeded_tags,
            seeded_companies=seeded_companies,
            seeded_locations=seeded_locations,
        ),
    )

    # Avoid race condition while it populated through search DBs
    time.sleep(1.5)

    yield seeded

    # If the inv has been used in a formulation, it cannot be deleted and will give a BadRequestError
    _delete_all(
        lambda inventory: client.inventory.delete(id=inventory.id),
        seeded,
        NotFoundError,
        BadRequestError,
    )


@pytest.fixture(scope="session")
def seeded_parameters(client: Albert, seed_prefix: str) -> Iterator[list[Parameter]]:
    def _seed(parameter: Parameter) -> Parameter:
        created_parameter = client.parameters.get_or_create(parameter=parameter)
        # Extra get_by_id is required to populate the category field on parameter
        return client.parameters.get_by_id(id=created_parameter.id)

    seeded = _pmap(_seed, generate_parameter_seeds(seed_prefix))

    # Avoid race condition while it populated through search DBs
    time.sleep(1.5)

    yield seeded

    _delete_all(lambda parameter: client.parameters.delete(id=parameter.id), seeded, NotFoundError)


@pytest.fixture(scope="session")
def seeded_parameter_groups(
    client: Albert,
    seed_prefix: str,
    seeded_parameters,
    seeded_tags,
    seeded_units,
    static_consumeable_parameter: Parameter,
    static_custom_fields: list[CustomField],
    static_lists: list[ListItem],
) -> Iterator[list[ParameterGroup]]:
    seeded = _pmap(
        lambda parameter_group: client.parameter_groups.create(parameter_group=parameter_group),
        generate_parameter_group_seeds(
            seed_prefix=seed_prefix,
            seeded_parameters=seeded_parameters,
            seeded_tags=seeded_tags,
            seeded_units=seeded_units,
            static_consumeable_parameter=static_consumeable_parameter,
            static_custom_fields=static_custom_fields,
            static_lists=static_lists,
        ),
    )

    # Avoid race condition while it populates through DBs
    time.sleep(1.5)

    yield seeded

    _delete_all(
        lambda parameter_group: client.parameter_groups.delete(id=parameter_group.id),
        seeded,
        NotFoundError,
    )


# PUT on lots is currently bugged. Teams discussion ongoing
@pytest.fixture(scope="session")
def seeded_lots(
    client: Albert,
    seeded_inventory,
    seeded_storage_locations,
    seeded_locations,
) -> Iterator[list[Lot]]:
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
def seeded_notebooks(
    client: Albert,
    seed_prefix: str,
    seeded_projects,
):
    def _seed(nb):
        seed = client.notebooks.create(notebook=nb)
        seed.blocks = generate_notebook_block_seeds()  # generate each iteration for new block ids
        return client.notebooks.update_block_content(notebook=seed)

    seeded = _pmap(
        _seed, generate_notebook_seeds(seed_prefix=seed_prefix, seeded_projects=seeded_projects)
    )
    yield seeded
    _delete_all(lambda notebook: client.notebooks.delete(id=notebook.id), seeded, NotFoundError)


@pytest.fixture(scope="session")
def seeded_pricings(client: Albert, seed_prefix: str, seeded_inventory, seeded_locations):
    seeded = _pmap(
        lambda p: client.pricings.create(pricing=p),
        generate_pricing_seeds(seed_prefix, seeded_inventory, seeded_locations),
    )
    yield seeded
    _delete_all(lambda p: client.pricings.delete(id=p.id), seeded, NotFoundError)


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
        for x in client.inventory.get_all(
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
    static_lists: list[ListItem],
    static_custom_fields: list[CustomField],
):
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
        static_lists=static_lists,
        static_custom_fields=static_custom_fields,
    )
    seeded = _pmap(lambda t: client.tasks.create(task=t), all_tasks)
    yield seeded
    _delete_all(lambda t: client.tasks.delete(id=t.id), seeded, NotFoundError, BadRequestError)


@pytest.fixture(scope="session")
def seeded_entity_types(
    client: Albert,
    seed_prefix: str,
    static_entity_custom_fields: list[CustomField],
) -> Iterator[list[EntityType]]:
    # Sequential on purpose: the entitytypes endpoint 500s under concurrent creates
    seeded = [
        client.entity_types.create(entity_type=entity_type)
        for entity_type in generate_entity_type_seeds(
            seed_prefix=seed_prefix,
            static_entity_custom_fields=static_entity_custom_fields,
        )
    ]
    yield seeded
    _delete_all(
        lambda entity_type: client.entity_types.delete(id=entity_type.id), seeded, NotFoundError
    )


@pytest.fixture(scope="session")
def seeded_notes(
    client: Albert,
    seeded_tasks: list[BaseTask],
    seeded_inventory: list[InventoryItem],
    seed_prefix: str,
):
    seeded = _pmap(
        lambda note: client.notes.create(note=note),
        generate_note_seeds(
            seeded_tasks=seeded_tasks, seeded_inventory=seeded_inventory, seed_prefix=seed_prefix
        ),
    )
    yield seeded
    _delete_all(lambda note: client.notes.delete(id=note.id), seeded, NotFoundError)


@pytest.fixture(scope="session")
def attachment_note(
    client: Albert,
    seeded_inventory: list[InventoryItem],
    seed_prefix: str,
) -> Iterator[Note]:
    note = Note(
        parent_id=seeded_inventory[0].id,
        note=f"{seed_prefix}-attachments",
    )
    created = client.notes.create(note=note)
    yield created
    with suppress(NotFoundError):
        client.notes.delete(id=created.id)


@pytest.fixture(scope="session")
def seeded_links(client: Albert, seeded_tasks: list[BaseTask]):
    seeded = client.links.create(links=generate_link_seeds(seeded_tasks=seeded_tasks))
    yield seeded
    for link in seeded:
        with suppress(NotFoundError):
            client.links.delete(id=link.id)


@pytest.fixture(scope="session")
def seeded_btdataset(client: Albert, seed_prefix: str) -> Iterator[BTDataset]:
    dataset = generate_btdataset_seed(seed_prefix)
    dataset = client.btdatasets.create(dataset=dataset)
    yield dataset
    client.btdatasets.delete(id=dataset.id)


@pytest.fixture(scope="session")
def seeded_btmodelsession(
    client: Albert,
    seed_prefix: str,
    seeded_btdataset: BTDataset,
) -> Iterator[BTModelSession]:
    model_session = generate_btmodelsession_seed(seed_prefix, seeded_btdataset)
    model_session = client.btmodelsessions.create(model_session=model_session)
    yield model_session
    client.btmodelsessions.delete(id=model_session.id)


@pytest.fixture(scope="session")
def seeded_btmodel(
    client: Albert,
    seed_prefix: str,
    seeded_btdataset: BTDataset,
    seeded_btmodelsession: BTModelSession,
) -> Iterator[BTModel]:
    model = generate_btmodel_seed(seed_prefix, seeded_btdataset)
    model = client.btmodels.create(model=model, parent_id=seeded_btmodelsession.id)
    yield model
    client.btmodels.delete(id=model.id, parent_id=seeded_btmodelsession.id)


@pytest.fixture(scope="session")
def seeded_btinsight(
    client: Albert,
    seed_prefix: str,
    seeded_btdataset: BTDataset,
    seeded_btmodelsession: BTModel,
) -> Iterator[BTInsight]:
    ins = generate_btinsight_seed(seed_prefix, seeded_btdataset, seeded_btmodelsession)
    ins = client.btinsights.create(insight=ins)
    time.sleep(3.0)
    yield ins
    client.btinsights.delete(id=ins.id)


@pytest.fixture(scope="session")
def seeded_reports(
    client: Albert,
    seed_prefix: str,
    seeded_projects: list[Project],
) -> Iterator[list[FullAnalyticalReport]]:
    """Create seeded reports for testing."""
    seeded = _pmap(
        lambda report: client.reports.create_report(report=report),
        generate_report_seeds(seed_prefix=seed_prefix, seeded_projects=seeded_projects),
    )

    yield seeded

    _delete_all(lambda report: client.reports.delete(id=report.id), seeded, NotFoundError)


@pytest.fixture(scope="session")
def seeded_targets(
    client: Albert,
    seed_prefix: str,
    seeded_data_templates: list[DataTemplate],
) -> Iterator[list[Target]]:
    seeded = _pmap(
        lambda target: client.targets.create(target=target),
        generate_target_seeds(
            seed_prefix=seed_prefix,
            seeded_data_templates=seeded_data_templates,
        ),
    )
    yield seeded
    _delete_all(
        lambda target: client.targets.delete(id=target.id), seeded, NotFoundError, BadRequestError
    )


@pytest.fixture(scope="session")
def seeded_smart_dataset(
    client: Albert,
    seeded_projects: list[Project],
    seeded_targets: list[Target],
) -> Iterator[SmartDataset]:
    scope = generate_smart_dataset_seed(
        seeded_projects=seeded_projects,
        seeded_targets=seeded_targets,
    )
    created = client.smart_datasets.create(scope=scope, build=False)
    yield created
    with suppress(NotFoundError, BadRequestError):
        client.smart_datasets.delete(id=created.id)


@pytest.fixture(scope="session")
def seeded_built_smart_dataset(
    client: Albert,
    seeded_projects: list[Project],
    seeded_targets: list[Target],
) -> Iterator[SmartDataset]:
    scope = generate_smart_dataset_seed(
        seeded_projects=seeded_projects,
        seeded_targets=seeded_targets,
    )
    created = client.smart_datasets.create(scope=scope, build=True)
    deadline = time.monotonic() + 10
    while created.build_state != SmartDatasetBuildState.READY and time.monotonic() < deadline:
        time.sleep(2)
        created = client.smart_datasets.get_by_id(id=created.id)
    yield created
    with suppress(NotFoundError, BadRequestError):
        client.smart_datasets.delete(id=created.id)


@pytest_asyncio.fixture(scope="function")
async def seeded_folder(
    async_client: AsyncAlbert, seed_prefix: str
) -> AsyncGenerator[ChatFolder, None]:
    folder = await async_client.chat_folders.create(
        folder=ChatFolder(name=f"{seed_prefix} Chat Folder")
    )
    yield folder
    with suppress(NotFoundError):
        await async_client.chat_folders.delete(id=folder.id)


@pytest_asyncio.fixture(scope="function")
async def seeded_session(
    async_client: AsyncAlbert, seed_prefix: str, seeded_folder: ChatFolder
) -> AsyncGenerator[ChatSession, None]:
    session = await async_client.chat_sessions.create(
        session=ChatSession(
            name=f"{seed_prefix} Chat Session",
            parent_id=seeded_folder.id,
            source_session_id=str(uuid.uuid4()),
        )
    )
    yield session
    with suppress(NotFoundError):
        await async_client.chat_sessions.delete(id=session.id)


@pytest_asyncio.fixture(scope="function")
async def seeded_message(
    async_client: AsyncAlbert, seeded_session: ChatSession
) -> AsyncGenerator[ChatMessage, None]:
    message = await async_client.chat_messages.create(
        message=ChatMessage(
            component_type=ChatComponentType.TEXT,
            user_type=ChatUserType.USER,
            role=ChatRole.USER,
            content={"message": "Hello from SDK tests"},
            parent_id=seeded_session.id,
            sequence="000",
        )
    )
    yield message
