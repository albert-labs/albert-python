# Increased Intervals

This guide is for you if increased intervals is enabled for your tenant and you create or
edit **Property tasks** or **Batch tasks** with the Albert Python SDK. If your tenant does
not have the feature, nothing here applies and your existing code keeps working.

## Do you need to do anything?

Upgrade to SDK version **1.77.0** or later. It is the minimum version for tenants with
increased intervals.

With increased intervals, every block of a Property or Batch task needs its interval
**combinations** generated before it can show rows or take results. Older SDK versions do
not generate them when you call `create`, `create_many`, `add_block`, `add_blocks` or
`update_block_workflow`: the block is saved, but it stays on "Loading data" in Albert and
no error is raised. From version 1.77.0, these methods generate the combinations of the
blocks they add or change before they return.

- **None of your tasks use intervalized parameters:** no call-site changes for new tasks.
  Still check the existing-block warning below.
- **Your tasks use intervals:** upgrade, then read [If you use intervals](#if-you-use-intervals).

General tasks hold no blocks and are not affected.

!!! note "Creating tasks and changing blocks takes longer"
    `create`, `create_many`, `add_block`, `add_blocks` and `update_block_workflow` now wait
    until the combinations of each block are generated. Generation jobs for multiple blocks
    of one task start at least 10 seconds apart. Pass `wait=False` to return after the
    generation jobs have been submitted. A failure that happens later is not raised by that
    call. The blocks of tasks returned by `create` and `create_many` carry the submitted
    job's `job_id` and `job_state`.

!!! warning "Blocks created with an older SDK version"
    Upgrading does not repair blocks that an older version already created on your tenant.
    Generate their combinations once with `generate_block_combinations`. If you do this for
    several blocks of the same task, leave at least 10 seconds between calls.

    ```python
    from albert import Albert

    client = Albert()
    client.tasks.generate_block_combinations(task_id="TAS123", block_id="BLK1")
    ```

---

## Quick reference

| Action | Increased intervals not enabled | Increased intervals enabled |
|---|---|---|
| Create a General task | `create` | `create` |
| Create a Property or Batch task | `create` | `create` |
| Create a task with rules or overrides | Not applicable | `create_with_combinations` |
| Create several tasks | `create_many` | `create_many` |
| Add blocks | `add_block` / `add_blocks` | `add_block` / `add_blocks` |
| Change a block's workflow | `update_block_workflow` | `update_block_workflow` |
| Change a block's rules or overrides | Not applicable | `set_block_rules` |
| Retry after a generation failure | Not applicable | `generate_block_combinations` |
| Remove a block | `remove_block` | `remove_block` |

---

## Handle generation failures

When generation cannot be started, or with `wait=True` when a job fails, does not finish
in time or cannot be monitored, `create`, `create_many`, `create_with_combinations`,
`add_block`, `add_blocks` and `update_block_workflow` raise `CombinationGenerationError`
after trying every selected block. With `wait=False`, only failures to start generation
are included; later job failures are not. The task or block already exists, so retry only
the failed blocks with `generate_block_combinations`. It keeps interval barcodes. If
waiting times out or monitoring fails, the job may still be running; check it before
retrying.

`err.failed_blocks` is empty after `add_block` or `add_blocks` only when Albert did not
report which blocks were added. Generate combinations for the blocks on `err.task.blocks`
that were not on the task before the call.

```python
import time

from albert import Albert
from albert.exceptions import CombinationGenerationError
from albert.resources.tasks import Block, PropertyTask

client = Albert()
task_definition = PropertyTask(
    name="Viscosity screen",
    parent_id="PRO123",
    blocks=[Block(data_template=[{"id": "DAT123"}], workflow=[{"id": "WFL456"}])],
)

try:
    task = client.tasks.create(task=task_definition)
except CombinationGenerationError as err:
    task = err.task
    for block_id in err.failed_blocks:
        client.tasks.generate_block_combinations(task_id=task.id, block_id=block_id)
        time.sleep(10)  # leave 10 seconds between blocks of the same task
```

!!! danger "Do not repeat the call after a failure"
    Calling `create`, `create_many` or `create_with_combinations` again creates a second
    task, and calling `add_block` or `add_blocks` again adds a second block.

From `create_many`, `err.task` is `None`. The tasks are on `err.tasks`, and each entry of
`err.failed_blocks` names its task as `TAS.../BLK...`:

```python
try:
    tasks = client.tasks.create_many(tasks=[task_definition])
except CombinationGenerationError as err:
    tasks = err.tasks
    for entry in err.failed_blocks:
        task_id, block_id = entry.split("/")
        client.tasks.generate_block_combinations(task_id=task_id, block_id=block_id)
        time.sleep(10)
```

---

## If you use intervals

This section is for code that works with intervalized parameters, for example code that
gets a `ROW` chain such as `ROW3XROW6` from `Workflow.get_interval_id` and writes or reads
results by it. Most of that code keeps working; the changes are below.

### Rules and overrides

By default, `create`, `create_many`, `add_block` and `add_blocks` generate combinations
without adding rules or overrides. `create` and `create_many` preserve the block's
`intervals_start_from` baseline. `add_block` and `add_blocks` use the new block's baseline,
which defaults to `"all"`. To apply rules or overrides:

- When you create the task, use `create_with_combinations`, with the rules and overrides on
  the blocks.
- On an existing block, use `set_block_rules`. It regenerates the combinations for you,
  unless you pass `generate_combinations=False`. In that case call
  `generate_block_combinations` once you are done.

See [Intervals, Rules, and Overrides](../examples/tasks.md) for examples.

### Reading results

With increased intervals, Albert stores each result under its combination's child workflow
(`WFL...`), so reads report the interval as that child workflow ID, not as a `ROW` chain.
This applies to `interval_combination` from `property_data.get_task_property_records` and
to the raw reads, `property_data.get_all_task_properties` and
`property_data.get_task_block_properties`. Code that matches results on `ROW` chains finds
none.

`get_task_property_records` adds `interval_row_key` and resolves `parameter_setpoints`
when it can map the interval to the workflow:

```python
records = client.property_data.get_task_property_records(task_id="TAS123")
for record in records:
    print(record.interval_combination, record.interval_row_key, record.parameter_setpoints)
# WFL999 ROW3XROW6 {'Temperature': '25', 'Time': '60'}
```

- If your code matches results by `ROW` chain, match on `interval_row_key` instead of
  `interval_combination`. The value is `None` for `"default"` and when the ROW chain cannot
  be resolved; `parameter_setpoints` is empty when the setpoints cannot be resolved.
- For raw reads, match the child workflow ID against `id` from `get_block_combinations`.
  The matching combination's `interval_row_key` gives its ROW chain. Alternatively, use
  `get_task_property_records`, which does this mapping for you.
- If your code already matches child workflow IDs in `interval_combination`, it keeps working.

### Writing, voiding and checking results

Writing and updating results, voiding and unvoiding accept a `ROW` chain, a child workflow
ID or an interval barcode, so code that writes or updates results by `ROW` chain keeps
working. `update_or_create_task_properties` finds an existing trial whichever form you pass.
Interval checks accept a `ROW` chain or child workflow ID and report the interval back as
its child workflow ID.

### Scripts that parse import metadata

For Property tasks, `import_results` with `mode=ImportMode.SCRIPT` switches to the newer
metadata format on its own for blocks with increased intervals, so your calls don't change.
`import_results` does not support Batch tasks; use `batch_data` for those. Scripts that read
the metadata themselves have a separate migration. Ask your Albert representative if you
have not received it.

---

## Workflow changes and barcodes

- When you change a block's workflow, each combination of the new workflow keeps the
  interval barcode and results of its best-matching combination in the replaced workflow.
  Old combinations that are not carried forward are removed, and their results are voided.
- The best match can differ in setpoints the new workflow fixes or no longer varies. For
  example, a result measured at Volume 25 can land on a combination where Volume is fixed
  at 30. Check carried-over results after a workflow change.
- Generating a block's combinations again, for example after a rules change, keeps the
  barcodes of combinations that remain.
- If generation fails after a workflow change, run `generate_block_combinations` for the
  block soon. Barcodes are kept, but results entered before the change may not move to the
  new combinations; check them and enter any that are missing again.

!!! note "Usually leave `old_workflow_id` unset"
    `update_block_workflow` supplies the replaced workflow automatically, and direct
    `generate_block_combinations` calls can use the previous workflow recorded on the
    block, including when another script or an older SDK version changed it.
    `set_block_rules` uses the block's current workflow when regenerating rules. Pass
    `old_workflow_id` to `generate_block_combinations` or `set_block_rules` only when you
    need to select a specific earlier workflow yourself.

---

## New capabilities

These are optional and need increased intervals. They are not part of the migration.

- Rules and overrides decide which combinations a block keeps: `create_with_combinations`,
  `set_block_rules`, `get_block_rules`, and the `Workflow.build_rule`,
  `Workflow.build_rule_condition` and `Workflow.build_override` helpers.
- Inventory exclusions omit selected inventory-and-combination pairs from property-data
  grids, exports and data-completeness checks: `add_block_inventory_exclusions` and
  `remove_block_inventory_exclusions`. They do not reduce the number of combinations
  generated for the block.
- Every combination has a persistent interval barcode, listed by `get_block_combinations`.
- A block holds at most **2,000** combinations after rules and overrides. Above that,
  generation fails.

---

## What changed in the SDK

- `create`, `create_many`, `add_block`, `add_blocks` and `update_block_workflow` generate
  the combinations of the blocks they add or change, and take a `wait` keyword (default
  `True`).
- `add_block` returns the new block ID, and `add_blocks` returns the new block IDs in the
  order given. Both returned `None` before.
- `CombinationGenerationError` is raised by the methods above when generation fails or
  cannot be started. It carries `task`, `tasks`, `failed_blocks` and `job_states`.
- `TaskPropertyRecord.interval_row_key` gives the resolved `ROW` chain of a record's
  interval, and `parameter_setpoints` is now filled when the setpoints can be resolved.
  `interval_combination` is unchanged.
- `update_or_create_task_properties` updates the existing trial when its interval is given
  as a `ROW` chain or interval barcode, instead of adding a new trial.
- `Block.combinations_mode` (`"child_workflows"` or `"legacy"`) and
  `Block.previous_workflow_id` are new read-only fields.
- `update_block_workflow` and `generate_block_combinations` work on blocks that use the
  default "No Parameter Group" workflow.

---

## Property tasks and Batch tasks

Both task types follow the same steps.

| | Property task | Batch task |
|---|---|---|
| Combinations generated by `create`, `add_block(s)`, `update_block_workflow` | Yes | Yes |
| Rules, overrides, `intervals_start_from` | Supported | Supported |
| Combination cap per block | 2,000 | 2,000 |

A Batch task still needs `batch_size_unit` and `inventory_information`.

---

## If you call the Albert API directly

`combinationsMode` and `previousWorkflowId` on a block are read-only. Do not send them back
when you create a task or add a block; Albert rejects them.

---

## Migration checklist

- [ ] SDK upgraded to 1.77.0 or later
- [ ] Combinations generated once for blocks an older SDK version created on your tenant
- [ ] `wait` decided for each `create`, `create_many`, `add_block`, `add_blocks` and `update_block_workflow` call
- [ ] `CombinationGenerationError` handled, with retries limited to the failed blocks
- [ ] Rules and overrides applied with `create_with_combinations` or `set_block_rules`
- [ ] Code that matches results by `ROW` chain reads `interval_row_key` from `get_task_property_records`
- [ ] Raw reads (`get_all_task_properties`, `get_task_block_properties`) use child workflow IDs, mapped through `get_block_combinations` when a ROW chain is needed

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| A block stays on "Loading data" | It was created by an older SDK version, or generation failed | Call `generate_block_combinations` for the block |
| `CombinationGenerationError` after `create` | Generation failed on one or more blocks; the task exists | Retry `err.failed_blocks` with `generate_block_combinations` |
| `create_with_combinations` rejects the task | Increased intervals is not enabled for the tenant | Use `create` |
| `TypeError` from a combination method | The task is a General task | Combinations apply to Property and Batch tasks only |
| Generation fails above 2,000 combinations | The block exceeds the cap | Add rules or overrides to reduce combinations |
| Interval IDs are `WFL...`, not `ROW` chains | Results are stored by child workflow | Match on `interval_row_key` from `get_task_property_records`, or on the child workflow ID |

If you run into any issues, please open a [GitHub issue](https://github.com/albert-labs/albert-python/issues).
