from albert.client import Albert
from albert.resources.data_templates import DataTemplate
from albert.resources.projects import Project
from albert.resources.smart_projects import SmartProject
from albert.resources.targets import Target, TargetOperator, TargetType, TargetValue


def _scope_target_ids(smart: SmartProject) -> set[str]:
    """Collect the target IDs in a smart project's scope."""
    if smart.scope is None:
        return set()
    return set(smart.scope.targets)


def _add_new_target(smart: SmartProject, target: Target) -> str:
    """Create a new target on a smart project and return its newly assigned ID."""
    before = _scope_target_ids(smart)
    after = _scope_target_ids(smart.add_target(target=target))
    new_ids = after - before
    assert len(new_ids) == 1
    return new_ids.pop()


def test_get_smart(client: Albert, seeded_projects: list[Project]):
    """Test retrieving smart project metadata."""
    project = seeded_projects[0]
    smart = project.smart
    assert isinstance(smart, SmartProject)
    assert smart.project_id == project.id


def test_add_target(
    client: Albert,
    seed_prefix: str,
    seeded_projects: list[Project],
    seeded_data_templates: list[DataTemplate],
):
    """Test creating a new target through a smart project's scope."""
    project = seeded_projects[0]
    smart = project.smart

    number_template = [
        x for x in seeded_data_templates if x.name == f"{seed_prefix} - Number Validation Template"
    ].pop()
    number_data_column = number_template.data_column_values[0]

    target = Target(
        name=f"{seed_prefix} - Smart Project Target",
        data_template_id=number_template.id,
        data_column_id=number_data_column.data_column_id,
        type=TargetType.PERFORMANCE,
        target_value=TargetValue(operator=TargetOperator.LTE, value=50),
        is_required=True,
    )
    target_id = _add_new_target(smart, target)
    assert target_id.startswith("TAR")

    smart.remove_target(target=target_id, delete=True)


def test_update_smart_dataset(
    client: Albert,
    seed_prefix: str,
    seeded_projects: list[Project],
    seeded_data_templates: list[DataTemplate],
):
    """Test creating a dataset from a smart project's scope and attaching one by ID."""
    project = seeded_projects[0]
    smart = project.smart

    number_template = [
        x for x in seeded_data_templates if x.name == f"{seed_prefix} - Number Validation Template"
    ].pop()
    number_data_column = number_template.data_column_values[0]
    target_id = _add_new_target(
        smart,
        Target(
            name=f"{seed_prefix} - Dataset Target",
            data_template_id=number_template.id,
            data_column_id=number_data_column.data_column_id,
            type=TargetType.PERFORMANCE,
            target_value=TargetValue(operator=TargetOperator.EQ, value=1),
            is_required=False,
        ),
    )

    # No dataset -> build a new smart dataset from the current scope.
    smart.update_dataset()
    assert smart.dataset_id is not None
    assert smart.dataset_id.startswith("SDT")

    # The built dataset can be retrieved.
    dataset = client.smart_datasets.get_by_id(id=smart.dataset_id)
    assert dataset.id == smart.dataset_id

    # Explicit dataset ID -> attach that dataset to the smart record.
    dataset_id = smart.dataset_id
    smart.update_dataset(dataset=dataset_id)
    assert smart.dataset_id == dataset_id

    smart.remove_target(target=target_id, delete=True)


def test_remove_and_readd_target(
    client: Albert,
    seed_prefix: str,
    seeded_projects: list[Project],
    seeded_data_templates: list[DataTemplate],
):
    """Test removing and re-adding an existing target by ID in the smart scope."""
    project = seeded_projects[0]
    smart = project.smart

    number_template = [
        x for x in seeded_data_templates if x.name == f"{seed_prefix} - Number Validation Template"
    ].pop()
    number_data_column = number_template.data_column_values[0]
    target_id = _add_new_target(
        smart,
        Target(
            name=f"{seed_prefix} - Patch Target",
            data_template_id=number_template.id,
            data_column_id=number_data_column.data_column_id,
            type=TargetType.PERFORMANCE,
            target_value=TargetValue(operator=TargetOperator.GTE, value=1),
            is_required=False,
        ),
    )

    removed = smart.remove_target(target=target_id)
    assert target_id not in _scope_target_ids(removed)

    readded = smart.add_target(target=target_id)
    assert target_id in _scope_target_ids(readded)

    smart.remove_target(target=target_id, delete=True)
