from contextlib import suppress

import pytest

from albert import Albert
from albert.exceptions import BadRequestError, NotFoundError
from albert.resources.batch_data import (
    BatchData,
    BatchDataLotUsage,
    BatchDataProduct,
    BatchValueId,
    BatchValuePatchDatum,
    BatchValuePatchPayload,
)
from albert.resources.tasks import (
    BaseTask,
    BatchSizeUnit,
    BatchTask,
    Block,
    TaskCategory,
    TaskInventoryInformation,
    TaskPriority,
)

pytestmark = pytest.mark.xdist_group("tasks")


def _seeded_batch_task(seeded_tasks: list[BaseTask]) -> BatchTask:
    return [t for t in seeded_tasks if isinstance(t, BatchTask)][0]


def _create_batch_task(
    client: Albert,
    *,
    seed_prefix: str,
    name_suffix: str,
    seeded_products,
    seeded_projects,
    seeded_locations,
    static_user,
    blocks: list | None = None,
) -> BatchTask:
    """Create a private batch task on the seeded formula for mutating batch data tests."""
    formula = seeded_products[0]
    project = seeded_projects[0]
    return client.tasks.create(
        task=BatchTask(
            name=f"{seed_prefix} - {name_suffix}",
            category=TaskCategory.BATCH,
            batch_size_unit=BatchSizeUnit.GRAMS,
            inventory_information=[
                TaskInventoryInformation(inventory_id=formula.id, batch_size=50.0)
            ],
            location=seeded_locations[0],
            priority=TaskPriority.LOW,
            project=project,
            parent_id=project.id,
            assigned_to=static_user,
            due_date="2024-10-31",
            blocks=blocks,
        )
    )


def _ensure_batch_data(client: Albert, task_id: str) -> None:
    """Initialize the batch data grid when task creation did not already do it."""
    with suppress(NotFoundError):
        grid = client.batch_data.get_by_id(id=task_id)
        if grid.product:
            return
    with suppress(BadRequestError):
        # Batch data creation is not idempotent ("already exist").
        client.batch_data.create_batch_data(task_id=task_id)


def test_get_by_id(client: Albert, seeded_tasks: list[BaseTask]):
    batch_task = [t for t in seeded_tasks if isinstance(t, BatchTask)][0]
    batch_data = client.batch_data.get_by_id(id=batch_task.id)
    assert batch_data.id == batch_task.id


@pytest.mark.xfail(
    reason="Batch data creation is currently not idempotent, so this test may fail if batch data already exists for the task."
)
def test_create_batch_data(client: Albert, seeded_tasks: list[BaseTask]):
    batch_tasks = [t for t in seeded_tasks if isinstance(t, BatchTask)]

    for bt in batch_tasks:
        # Check that the batch data is empty
        existing_batch_data = client.batch_data.get_by_id(id=bt.id)
        if len(existing_batch_data.product) == 0:
            try:
                client.batch_data.create_batch_data(task_id=bt.id)
            except BadRequestError as exc:
                if "already exist" not in str(exc):
                    raise
            created_batch_data = client.batch_data.get_by_id(id=bt.id)
            # Make sure it was created
            assert isinstance(created_batch_data, BatchData)
            assert len(created_batch_data.product) > 0


def test_update_batch_data(client: Albert, seeded_tasks: list[BaseTask]):
    batch_task = [t for t in seeded_tasks if isinstance(t, BatchTask)][0]

    existing_batch_data = client.batch_data.get_by_id(id=batch_task.id)

    if existing_batch_data.product == []:
        existing_batch_data = client.batch_data.create_batch_data(task_id=batch_task.id)

    # Check that there is no lot/batch info to start
    for row in existing_batch_data.rows:
        assert len(row.child_rows) == 0
    row_id = existing_batch_data.rows[0].row_id
    col_id = [x for x in existing_batch_data.rows[0].values if x.type == "INV"][0].col_id
    inv_id = [x for x in existing_batch_data.rows[0].values if x.type == "INV"][0].id
    value = [x for x in existing_batch_data.rows[0].values if x.type == "INV"][0].value
    lot = next(client.lots.get_all(parent_id=inv_id))
    patch = BatchValuePatchPayload(
        id=BatchValueId(col_id=col_id, row_id=row_id),
        data=[
            BatchValuePatchDatum(
                operation="add",
                attribute="lotId",
                lot_id=lot.id,
                newValue=value,
            )
        ],
    )

    client.batch_data.update_used_batch_amounts(task_id=batch_task.id, patches=[patch])
    updated_batch_data = client.batch_data.get_by_id(id=batch_task.id)
    # Check that there is now lot/batch info
    found = False
    for row in updated_batch_data.rows:
        if len(row.child_rows) > 0:
            found = True
            assert row.child_rows[0].id == lot.id
            assert row.row_id == row_id
            for val in row.child_rows[0].values:
                if val.col_id == col_id:
                    assert val.value == value
                    assert val.type == "INV"
                    assert val.id == inv_id
    assert found


def test_get_lookup_column(client: Albert, seeded_tasks: list[BaseTask]):
    """Get the lookup column data of the seeded batch task."""
    batch_task = _seeded_batch_task(seeded_tasks)

    lookup = client.batch_data.get_lookup_column(id=batch_task.id)

    assert isinstance(lookup, BatchData)
    assert lookup.id == batch_task.id


def test_get_by_lot_id(client: Albert, seeded_tasks: list[BaseTask]):
    """List the batch data usages of a lot of the seeded batch task's formula."""
    batch_task = _seeded_batch_task(seeded_tasks)
    grid = client.batch_data.get_by_id(id=batch_task.id)
    inv_id = [x for x in grid.rows[0].values if x.type == "INV"][0].id
    lot = next(client.lots.get_all(parent_id=inv_id))

    usages = list(client.batch_data.get_by_lot_id(id=lot.id))

    assert all(isinstance(u, BatchDataLotUsage) for u in usages)
    assert all(u.task_id and u.product.id for u in usages)


def test_update_batch_size(
    client: Albert,
    seed_prefix: str,
    seeded_products,
    seeded_projects,
    seeded_locations,
    static_user,
):
    """Update the batch size of a private batch task and rescale its amounts."""
    task = _create_batch_task(
        client,
        seed_prefix=seed_prefix,
        name_suffix="Batch Data Update Batch Size",
        seeded_products=seeded_products,
        seeded_projects=seeded_projects,
        seeded_locations=seeded_locations,
        static_user=static_user,
    )
    try:
        _ensure_batch_data(client, task.id)

        client.batch_data.update_batch_size(
            task_id=task.id, formula_id=seeded_products[0].id, new_value=100.0, old_value=50.0
        )

        updated = client.batch_data.get_by_id(id=task.id)
        assert any(
            float(col.reference_total) == pytest.approx(100.0)
            for col in updated.product
            if col.reference_total
        )
    finally:
        with suppress(NotFoundError, BadRequestError):
            client.tasks.delete(id=task.id)


def test_add_and_delete_block_column(
    client: Albert,
    seed_prefix: str,
    seeded_products,
    seeded_projects,
    seeded_locations,
    seeded_workflows,
    seeded_data_templates,
    static_user,
):
    """Add and remove the Batch Instructions block column of a private batch task."""
    task = _create_batch_task(
        client,
        seed_prefix=seed_prefix,
        name_suffix="Batch Data Block Column",
        seeded_products=seeded_products,
        seeded_projects=seeded_projects,
        seeded_locations=seeded_locations,
        static_user=static_user,
        blocks=[Block(workflow=[seeded_workflows[0]], data_template=[seeded_data_templates[0]])],
    )
    try:
        _ensure_batch_data(client, task.id)

        client.batch_data.add_products(
            id=task.id, products=[BatchDataProduct(name="Batch Instructions")]
        )
        client.batch_data.delete_products(id=task.id, products=[BatchDataProduct(col_id="COL3")])
    finally:
        with suppress(NotFoundError, BadRequestError):
            client.tasks.delete(id=task.id)


def test_update_column_sequence(
    client: Albert,
    seed_prefix: str,
    seeded_products,
    seeded_projects,
    seeded_locations,
    seeded_workflows,
    seeded_data_templates,
    static_user,
):
    """Move the product column of a private batch task after the block column."""
    task = _create_batch_task(
        client,
        seed_prefix=seed_prefix,
        name_suffix="Batch Data Column Sequence",
        seeded_products=seeded_products,
        seeded_projects=seeded_projects,
        seeded_locations=seeded_locations,
        static_user=static_user,
        blocks=[Block(workflow=[seeded_workflows[0]], data_template=[seeded_data_templates[0]])],
    )
    try:
        _ensure_batch_data(client, task.id)
        client.batch_data.add_products(
            id=task.id, products=[BatchDataProduct(name="Batch Instructions")]
        )
        grid = client.batch_data.get_by_id(id=task.id)
        product_col_id = grid.product[0].col_id

        client.batch_data.update_column_sequence(
            task_id=task.id, source_id=product_col_id, reference_id="COL3"
        )
    finally:
        with suppress(NotFoundError, BadRequestError):
            client.tasks.delete(id=task.id)


def test_resync_task(
    client: Albert,
    seed_prefix: str,
    seeded_products,
    seeded_projects,
    seeded_locations,
    static_user,
):
    """Sync the batch data of a private batch task with its design."""
    task = _create_batch_task(
        client,
        seed_prefix=seed_prefix,
        name_suffix="Batch Data Resync",
        seeded_products=seeded_products,
        seeded_projects=seeded_projects,
        seeded_locations=seeded_locations,
        static_user=static_user,
    )
    try:
        _ensure_batch_data(client, task.id)

        client.batch_data.resync_task(task_id=task.id)
    finally:
        with suppress(NotFoundError, BadRequestError):
            client.tasks.delete(id=task.id)


def test_delete_batch_data(
    client: Albert,
    seed_prefix: str,
    seeded_products,
    seeded_projects,
    seeded_locations,
    static_user,
):
    """Delete the batch data of a private batch task."""
    task = _create_batch_task(
        client,
        seed_prefix=seed_prefix,
        name_suffix="Batch Data Delete",
        seeded_products=seeded_products,
        seeded_projects=seeded_projects,
        seeded_locations=seeded_locations,
        static_user=static_user,
    )
    try:
        _ensure_batch_data(client, task.id)

        client.batch_data.delete(id=task.id)
    finally:
        with suppress(NotFoundError, BadRequestError):
            client.tasks.delete(id=task.id)
