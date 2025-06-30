from albert import Albert
from albert.resources.batch_data import (
    BatchData,
    BatchValueId,
    BatchValuePatchDatum,
    BatchValuePatchPayload,
)
from albert.resources.tasks import BaseTask, BatchTask


def test_get_by_id(client: Albert, seeded_tasks: list[BaseTask]):
    batch_task = [t for t in seeded_tasks if isinstance(t, BatchTask)][0]
    batch_data = client.batch_data.get_by_id(id=batch_task.id)
    assert batch_data.id == batch_task.id


def test_create_batch_data(client: Albert, seeded_tasks: list[BaseTask]):
    batch_tasks = [t for t in seeded_tasks if isinstance(t, BatchTask)]

    for bt in batch_tasks:
        # Check that the batch data is empty
        existing_batch_data = client.batch_data.get_by_id(id=bt.id)
        if len(existing_batch_data.product) == 0:
            client.batch_data.create_batch_data(task_id=bt.id)
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
        lotId=lot.id,
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
