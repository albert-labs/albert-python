# Increased Intervals

Use this guide if Albert has enabled increased intervals for your tenant and your code creates
or changes **Property** or **Batch** tasks, or reads or writes their results by interval.
Everything here applies to both task types. General tasks have no blocks and are not affected.

!!! abstract "What you need to do"
    1. [Upgrade to SDK 1.77.0 or later.](#1-upgrade-the-sdk) Older versions add blocks that
       stay on "Loading data" in Albert, with no error.
    2. [Expect calls that add or change blocks to take longer.](#2-expect-block-changes-to-wait-for-generation)
       They now wait until each block is ready for results.
    3. [Handle `CombinationGenerationError`, and never repeat the call that raised it.](#3-handle-combinationgenerationerror)
       The task or block already exists.
    4. [Match results on `interval_row_key`, not `interval_combination`.](#4-update-code-that-reads-results-by-interval)
       Reads now report intervals as child workflow IDs (`WFL...`), so code that compares
       them to ROW chains finds nothing.

    Writing, updating and voiding results by ROW chain keeps working; see
    [Writing and checking results](#writing-and-checking-results).

## Am I affected?

| Your situation | What to do |
|---|---|
| Increased intervals is not enabled for your tenant | Nothing. Upgrading is safe and your code keeps working. |
| Enabled, and your tasks have no intervalized parameters | Steps 1 to 3 |
| Enabled, and your code reads or writes results by interval | Steps 1 to 4 |

## Key terms

| Term | Example | What it is | Where you see it |
|---|---|---|---|
| Intervalized parameter | Temperature: 25, 60 | A workflow parameter with several values | The workflow |
| Combination | Temperature 25, Time 60 | One set of interval values that results are recorded under | `tasks.get_block_combinations` |
| Combination generation | | A background job that creates a block's combinations after the block is added or its workflow changes. Until it finishes, the block shows "Loading data" and takes no results. | `job_id` and `job_state` on a block |
| ROW chain | `ROW3XROW6` | Names a combination by the rows of its interval values | `Workflow.get_interval_id`, `interval_row_key` |
| Child workflow ID | `WFL999` | The workflow Albert creates for each combination. Results are stored under it. | `interval_combination` on reads, `id` from `get_block_combinations` |
| Interval barcode | `INab12CD34e` | A persistent, case-sensitive label for a combination | `interval_barcode` from `get_block_combinations` |
| `"default"` | `"default"` | The single interval of a block without intervalized parameters | `interval_combination` |

---

## Migration steps

### 1. Upgrade the SDK

=== "pip"

    ```bash
    pip install --upgrade "albert>=1.77.0"
    ```

=== "uv"

    ```bash
    uv add "albert>=1.77.0"
    ```

!!! warning "Older SDK versions fail silently"
    Enabling increased intervals does not upgrade your SDK. Versions before 1.77.0 save new
    blocks without generating their combinations: the block stays on "Loading data" in
    Albert and no error is raised.

### 2. Expect block changes to wait for generation

`create`, `create_many`, `create_with_combinations`, `add_block`, `add_blocks` and
`update_block_workflow` now generate the combinations of every block they add or change.
Each takes a `wait` keyword:

| | `wait=True` (default) | `wait=False` |
|---|---|---|
| Returns | When every block's combinations are generated | As soon as generation has started |
| Blocks ready for results on return | Yes | Not yet |
| Raises `CombinationGenerationError` when generation | could not start, failed, did not finish in time, or could not be monitored | could not start |

!!! note "Timing"
    Generation for blocks of the same task starts at least 10 seconds apart, so a task with
    4 blocks takes at least 30 seconds to create. Blocks of different tasks are not spaced
    out.

With `wait=False`, check on the blocks later with `tasks.get_by_id`. Each block carries
`job_id` and `job_state`:

```python
task = client.tasks.create(task=task_definition, wait=False)

task = client.tasks.get_by_id(id=task.id)
for block in task.blocks:
    print(block.id, block.job_state)
# BLK1 successful
```

### 3. Handle `CombinationGenerationError`

The methods in step 2 try every block, then raise `CombinationGenerationError` if any failed.
By then, the task or blocks were already created or changed.

!!! danger "Never repeat the call that raised it"
    Calling `create`, `create_many` or `create_with_combinations` again creates a second
    task. Calling `add_block` or `add_blocks` again adds a second block. Retry generation for
    the failed blocks only, with `generate_block_combinations`. It keeps interval barcodes.

=== "create"

    ```python
    import time

    from albert import Albert
    from albert.exceptions import CombinationGenerationError

    client = Albert()
    try:
        task = client.tasks.create(task=task_definition)
    except CombinationGenerationError as err:
        task = err.task  # the task exists
        for block_id in err.failed_blocks:
            client.tasks.generate_block_combinations(task_id=task.id, block_id=block_id)
            time.sleep(10)  # leave 10 seconds between blocks of the same task
    ```

=== "create_many"

    ```python
    try:
        tasks = client.tasks.create_many(tasks=[task_definition])
    except CombinationGenerationError as err:
        tasks = err.tasks  # err.task is None here
        for entry in err.failed_blocks:
            task_id, block_id = entry.split("/")  # entries name their task: TAS.../BLK...
            client.tasks.generate_block_combinations(task_id=task_id, block_id=block_id)
            time.sleep(10)
    ```

| Attribute | Contents |
|---|---|
| `task` | The task holding the failed blocks, fully populated. `None` from `create_many`. |
| `tasks` | Every task the call generated blocks for, fully populated |
| `failed_blocks` | IDs of the blocks to retry. From `create_many`, each entry is `TAS.../BLK...`. |
| `job_states` | The last known generation state of each block, keyed like `failed_blocks` |

!!! warning "A timed-out block may still be generating"
    A block is also listed in `failed_blocks` when waiting timed out or the connection
    dropped, even though its generation may still be running. Check its `job_state` with
    `tasks.get_by_id` first, and retry only blocks whose state is `"failed"`.

!!! note "Empty `failed_blocks` after `add_block` or `add_blocks`"
    This happens only when Albert did not report which blocks were added. Generate
    combinations for the blocks on `err.task.blocks` that were not on the task before the
    call.

### 4. Update code that reads results by interval

Albert now stores each result under its combination's child workflow ID. All three reads
report `interval_combination` in that form: `get_task_property_records`,
`get_all_task_properties` and `get_task_block_properties`.

!!! warning "Matching on ROW chains finds no results, with no error"
    Code that compares `interval_combination` with a ROW chain such as `ROW3XROW6` silently
    gets an empty result.

`get_task_property_records` gives each record its ROW chain in `interval_row_key`, on every
tenant. Match on it instead:

=== "Before"

    ```python
    row_chain = workflow.get_interval_id({"Temperature": 25, "Time": 60})
    values = [
        r.value
        for r in client.property_data.get_task_property_records(task_id="TAS123")
        if r.interval_combination == row_chain
    ]
    ```

=== "After"

    ```python
    row_chain = workflow.get_interval_id({"Temperature": 25, "Time": 60})
    values = [
        r.value
        for r in client.property_data.get_task_property_records(task_id="TAS123")
        if r.interval_row_key == row_chain
    ]
    ```

- `interval_row_key` is `None` for `"default"` and when Albert cannot resolve the ROW chain.
- `parameter_setpoints` names the interval's conditions, for example
  `{'Temperature': '25', 'Time': '60'}`. It is empty when they cannot be resolved.
- Code that already matches child workflow IDs keeps working.

The raw reads, `get_all_task_properties` and `get_task_block_properties`, report only the
child workflow ID. To get the ROW chain, map it through the block's combinations:

```python
row_chains = {
    combo.id: combo.interval_row_key
    for combo in client.tasks.get_block_combinations(task_id="TAS123", block_id="BLK1")
}
block = client.property_data.get_task_block_properties(
    inventory_id="INV123", task_id="TAS123", block_id="BLK1"
)
for interval in block.data:
    print(interval.interval_combination, row_chains.get(interval.interval_combination))
# WFL999 ROW3XROW6
```

!!! tip
    For code that runs on tenants with and without increased intervals, prefer
    `get_task_property_records`. It does this mapping for you.

---

## Writing and checking results

| Operation | ROW chain | Child workflow ID | Interval barcode |
|---|---|---|---|
| Write or update results: `add_properties_to_task`, `update_or_create_task_properties` | Yes | Yes | Yes |
| Void and unvoid: `void_interval_data`, `void_trial_data` and their `unvoid_` versions | Yes | Yes | Yes |
| Check for data: `check_block_interval_for_data` | Yes | Yes | No |

`update_or_create_task_properties` finds an existing trial whichever form you pass.

!!! note "Results imported with a script"
    For Property tasks, `import_results` with `mode=ImportMode.SCRIPT` switches to the newer
    metadata format on its own for blocks with increased intervals, so your calls don't
    change. Scripts that read that metadata themselves have a separate migration; ask your
    Albert representative if you have not received it. `import_results` does not support
    Batch tasks; use `batch_data` for those.

## Workflow changes and barcodes

When you change a block's workflow with `update_block_workflow`:

- Each combination of the new workflow keeps the interval barcode and results of its
  best-matching combination in the replaced workflow.
- Old combinations that are not carried forward are removed, and their results are voided.

When you regenerate a block's combinations with `generate_block_combinations`, or
`set_block_rules` regenerates them after a rules change, combinations that remain keep their
barcodes.

!!! warning "Check carried-over results after a workflow change"
    The best match can differ in setpoints the new workflow fixes or no longer varies. For
    example, a result measured at Volume 25 can land on a combination where Volume is fixed
    at 30.

!!! danger "If generation fails after a workflow change, regenerate soon"
    Barcodes are kept, but results entered before the change may not move to the new
    combinations. Run `generate_block_combinations` for the block, then check the results
    and enter any that are missing again.

!!! note "Leave `old_workflow_id` unset"
    `update_block_workflow` passes the replaced workflow for you, and
    `generate_block_combinations` uses the previous workflow recorded on the block, even when
    another script or an older SDK version changed it. Pass `old_workflow_id` to
    `generate_block_combinations` or `set_block_rules` only to select a specific earlier
    workflow.

## Rules, overrides and other new capabilities

By default, generation applies no rules or overrides. `create` and `create_many` keep each
block's `intervals_start_from` baseline; `add_block` and `add_blocks` use the new block's
baseline, which defaults to `"all"`. To apply rules or overrides, use
`create_with_combinations` when you create the task, or `set_block_rules` on an existing
block.

Increased intervals also brings rules and overrides, persistent interval barcodes, and a cap
of 2,000 combinations per block after rules and overrides. See
[Intervals, Rules, and Overrides](../examples/tasks.md#intervals-rules-and-overrides-overview)
for how they work, with examples. Inventory exclusions
([`add_block_inventory_exclusions`][albert.collections.tasks.TaskCollection.add_block_inventory_exclusions],
[`remove_block_inventory_exclusions`][albert.collections.tasks.TaskCollection.remove_block_inventory_exclusions])
leave selected inventory and combination pairs out of grids, exports and completeness checks.
They don't reduce the number of combinations.

## Other changes in 1.77.0

| Change | Details |
|---|---|
| `add_block` and `add_blocks` return block IDs | `add_block` returns the new block ID; `add_blocks` returns the new IDs in the order given. Both returned `None` before. |
| New read-only `Block` fields | `combinations_mode` (`"child_workflows"` or `"legacy"`) and `previous_workflow_id` |
| "No Parameter Group" blocks | `update_block_workflow` and `generate_block_combinations` work on blocks that use the default workflow |

!!! note "If you call the Albert API directly"
    `combinationsMode` and `previousWorkflowId` on a block are read-only. Do not send them
    when you create a task or add a block; Albert rejects them.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| A block stays on "Loading data" | It was added by an SDK older than 1.77.0, or its generation failed | Upgrade, then run `generate_block_combinations` for the block |
| No results when matching by ROW chain | Reads report child workflow IDs | [Step 4](#4-update-code-that-reads-results-by-interval) |
| Updating a trial adds a new trial instead | SDK older than 1.77.0, with a ROW chain or barcode | Upgrade |
| `create_with_combinations` rejects the task | Increased intervals is not enabled for the tenant | Use `create` |
| `TypeError` from a combination method | The task is a General task | Combinations apply to Property and Batch tasks only |
| Generation fails on a large workflow | More than 2,000 combinations after rules and overrides | Add rules or overrides to reduce them |

If you run into any issues, please open a [GitHub issue](https://github.com/albert-labs/albert-python/issues).
