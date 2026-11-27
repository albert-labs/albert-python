from contextlib import suppress

import pytest

from albert import Albert
from albert.core.shared.models.base import EntityLink
from albert.exceptions import BadRequestError, NotFoundError
from albert.resources.projects import Project
from albert.resources.sheets import CellType, Component, Row
from albert.resources.tasks import Block, PropertyTask, TaskCategory, TaskInventoryInformation

# Uses a private project and sheet (TAS rows cannot be removed from a sheet); grouped
# with tasks because that worker already builds the workflow and data template seeds.
pytestmark = pytest.mark.xdist_group("tasks")


def test_add_task_row(
    client: Albert,
    seed_prefix: str,
    seeded_locations,
    seeded_inventory,
    seeded_data_templates,
    seeded_workflows,
):
    """Test linking a property task into a sheet's Results section as a TAS row."""

    # Isolated project: TAS rows cannot be removed from a sheet, so the shared
    # seeded sheet must not be used.
    project = client.projects.create(
        project=Project(
            description=f"{seed_prefix} - add_task_row",
            locations=[EntityLink(id=seeded_locations[0].id)],
        )
    )
    task = None
    try:
        worksheet = client.worksheets.setup_worksheet(project_id=project.id, add_sheet=True)
        sheet = worksheet.sheets[0]

        column = sheet.add_formulation(
            formulation_name=f"{seed_prefix} - add_task_row formula",
            components=[Component(inventory_id=seeded_inventory[0].id, amount=100.0)],
        )

        task = client.tasks.create(
            task=PropertyTask(
                name=f"{seed_prefix} - add_task_row task",
                category=TaskCategory.PROPERTY,
                inventory_information=[TaskInventoryInformation(inventory_id=column.inventory_id)],
                parent_id=project.id,
                location=seeded_locations[0],
                blocks=[
                    Block(
                        workflow=[seeded_workflows[0]],
                        data_template=[seeded_data_templates[0]],
                    )
                ],
            )
        )

        row = sheet.add_task_row(task_id=task.id)
        assert isinstance(row, Row)
        assert row.type == CellType.TAS
        assert row.row_id.startswith("ROW")
        assert row.inventory_id == task.id

        sheet.grid = None
        result_row_ids = {r.row_id for r in sheet.result_design.rows}
        assert row.row_id in result_row_ids
    finally:
        if task is not None:
            with suppress(NotFoundError, BadRequestError):
                client.tasks.delete(id=task.id)
        with suppress(NotFoundError, BadRequestError):
            client.projects.delete(id=project.id)
