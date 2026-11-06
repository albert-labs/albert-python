# Increased Intervals (🧪Beta)

!!! warning "Beta Feature"
    Increased intervals is in beta and is enabled per tenant behind a platform feature flag.
    Do not use it in production without explicit guidance from Albert. The feature currently
    falls outside the Albert support contract, but we would love your feedback.

This guide is for you if your tenant now has increased intervals enabled and you create or
edit **Property tasks** or **Batch tasks** with the Albert Python SDK. It covers the changes
to make in your own code. If your tenant does not have the feature, nothing here applies and
your existing code keeps working.

## What's changing

With increased intervals, every Property and Batch task block needs its **combinations**
generated before it shows rows. A combination is one child workflow (`WFL...`) for each
distinct set of parameter setpoints on the block, and each one carries a persistent interval
barcode.

This applies even when a block's workflow has no intervals. Every block needs at least its
baseline combination.

Before, saving a block was enough. Now these calls still save the block, but they **do not**
generate its combinations:

- `tasks.create` and `tasks.create_many`
- `tasks.add_block` and `tasks.add_blocks`
- `tasks.update_block_workflow`

!!! danger "Blocks show no rows until combinations are generated"
    If you keep calling `create`, `create_many`, `add_block`, `add_blocks`, or
    `update_block_workflow` without the follow-up steps below, no error is raised. The
    block is saved, but it shows no rows and cannot take results. Check every call site.

General tasks are not affected.

---

## Quick reference

| Action | Increased intervals not enabled | Increased intervals enabled |
|---|---|---|
| Create a General task | `create` | `create` |
| Create a Property or Batch task with blocks | `create` | `create_with_combinations` |
| Create several Property or Batch tasks | `create_many` | `create_many`, then `generate_block_combinations` for each block |
| Add a block | `add_block` / `add_blocks` | Same, then `generate_block_combinations` |
| Change a block's workflow | `update_block_workflow` | Same, then `generate_block_combinations(old_workflow_id=<previous>)` |
| Change a block's rules or overrides | Not applicable | `set_block_rules` (regenerates automatically) |
| Remove a block | `remove_block` | `remove_block` |

---

## Migration steps

### 1. Confirm the feature is enabled

Albert enables increased intervals per tenant. If you are unsure whether it is on for yours,
ask your Albert representative before changing any code.

!!! warning "`create_with_combinations` rejects tenants without the feature"
    On a tenant without increased intervals, `create_with_combinations` rejects the task and
    nothing is created. If you run the same code against several tenants (for example
    development and production), choose the creation path from a setting in your own code
    rather than hard-coding it.

### 2. Find the affected call sites

Search your code for these calls and keep the ones that involve Property or Batch tasks:

```text
tasks.create(    tasks.create_many(    add_block    add_blocks    update_block_workflow
```

Calls that only create General tasks need no change.

### 3. Create tasks with blocks

Use `create_with_combinations` in place of `create`. It saves any unsaved workflows on your
blocks, creates the task, saves rules and overrides, generates combinations for every block,
and (by default) waits until generation finishes.

```python
from albert import Albert
from albert.resources.tasks import Block, PropertyTask

client = Albert.from_client_credentials(...)

# Before
task = client.tasks.create(
    task=PropertyTask(
        name="Viscosity screen",
        parent_id="PRO123",
        blocks=[Block(data_template=[{"id": "DAT123"}], workflow=[{"id": "WFL456"}])],
    )
)

# After
task = client.tasks.create_with_combinations(
    task=PropertyTask(
        name="Viscosity screen",
        parent_id="PRO123",
        blocks=[Block(data_template=[{"id": "DAT123"}], workflow=[{"id": "WFL456"}])],
    ),
    wait=True,
)
```

A Batch task works the same way. It still needs `batch_size_unit` and
`inventory_information`:

```python
from albert.resources.tasks import BatchSizeUnit, BatchTask, TaskInventoryInformation

task = client.tasks.create_with_combinations(
    task=BatchTask(
        name="Mixing speed batch",
        parent_id="PRO123",
        batch_size_unit=BatchSizeUnit.GRAMS,
        inventory_information=[TaskInventoryInformation(inventory_id="INVEXP123", batch_size=50.0)],
        blocks=[Block(data_template=[{"id": "DAT123"}], workflow=[{"id": "WFL456"}])],
    ),
    wait=True,
)
```

!!! note "Defaults and options"
    - Blocks that do not set `intervals_start_from` use Exclude mode (`"all"`). Set `"none"`
      for Include mode. See [Intervals, Rules, and Overrides](../examples/tasks.md).
    - With `wait=False`, the call returns right after submitting generation. Each block then
      carries `job_id` and `job_state` so you can track the work yourself.
    - Only `PropertyTask` and `BatchTask` are accepted. A `GeneralTask` raises `TypeError`.

### 4. Create several tasks at once

`create_many` does not generate combinations. Generate them for each block afterwards:

```python
tasks = client.tasks.create_many(tasks=[...])

for task in tasks:
    for block in task.blocks or []:
        client.tasks.generate_block_combinations(task_id=task.id, block_id=block.id)
```

!!! warning "Pace jobs on the same task"
    When you trigger generation for several blocks on one task, leave at least **10 seconds**
    between consecutive calls. `create_with_combinations` does this for you. Your own loops
    must add the pause.

### 5. Add or change blocks on an existing task

```python
# Add a block
client.tasks.add_block(task_id="TAS123", data_template_id="DAT123", workflow_id="WFL456")
task = client.tasks.get_by_id(id="TAS123")
new_block = task.blocks[-1]
client.tasks.generate_block_combinations(task_id=task.id, block_id=new_block.id)

# Change a block's workflow
client.tasks.update_block_workflow(task_id="TAS123", block_id="BLK1", workflow_id="WFL789")
client.tasks.generate_block_combinations(
    task_id="TAS123",
    block_id="BLK1",
    old_workflow_id="WFL456",  # the workflow you replaced
)
```

!!! note "Always pass `old_workflow_id` after a workflow swap"
    Passing the replaced workflow's ID keeps the interval barcodes of combinations whose
    setpoints did not change and removes the ones that no longer apply. Leave it unset for
    a block's first generation.

### 6. Use rules and overrides (optional)

Rules and overrides decide which combinations are kept. Build them with parameter names and
values using the helpers on `Workflow`, then save them with `set_block_rules`:

```python
workflow = client.workflows.get_by_id(id="WFL456")
rule = workflow.build_rule(name="Exclude hot runs", parameter="Temperature", operator=">=", value=90)

client.tasks.set_block_rules(task_id="TAS123", block_id="BLK1", rules=[rule])
```

- `set_block_rules` regenerates combinations for you. Pass `generate_combinations=False` to
  save the definitions only.
- Omitting `rules` or `overrides` leaves the existing ones untouched. Passing `[]` clears them.
- Overrides always take precedence over rules.
- A block can hold at most **2,000** combinations after rules and overrides. Above that,
  generation fails.

### 7. Handle generation failures

If `create_with_combinations(wait=True)` fails on one or more blocks, it raises
`CombinationGenerationError`. The task has already been created, so retry only the failed
blocks:

```python
from albert.exceptions import CombinationGenerationError

try:
    task = client.tasks.create_with_combinations(task=task_definition, wait=True)
except CombinationGenerationError as err:
    for block_id in err.failed_blocks:
        client.tasks.generate_block_combinations(task_id=err.task.id, block_id=block_id)
```

!!! danger "Do not call `create_with_combinations` again after a failure"
    The task already exists. Calling it again creates a duplicate task.

### 8. Update code that reads results

On increased-intervals tenants, results are addressed by **child workflow ID** (`WFL...`)
and barcode, not by interval row (`ROW#...`).

- Use `get_block_combinations` to list a block's combinations with their IDs and barcodes.
- Barcodes stay stable while a combination's parameter setpoints are unchanged.
- In the property data helpers, `parameter_setpoints` comes back **empty** on these tenants.
  Values and `interval_combination` are still present, so match results to conditions
  through the combination instead.

```python
for combo in client.tasks.get_block_combinations(task_id="TAS123", block_id="BLK1"):
    print(combo.id, combo.name, combo.interval_barcode)
```

### 9. Check custom templates and imports

- Custom templates gain `increased_intervals` and, per block, `intervals_start_from`,
  `rules`, and `overrides`. Existing templates keep working. Set these only when you want
  tasks created from a template to use combinations.
- `import_results` and script task metadata switch to the newer metadata format
  automatically for blocks that use increased intervals. You do not need to change your calls.

---

## Property tasks and Batch tasks

Both task types follow the same steps above.

| | Property task | Batch task |
|---|---|---|
| Create with blocks | `create_with_combinations` | `create_with_combinations` |
| Generate after `create_many`, `add_block(s)`, `update_block_workflow` | `generate_block_combinations` | `generate_block_combinations` |
| Rules, overrides, `intervals_start_from` | Supported | Supported |
| Combination cap per block | 2,000 | 2,000 |
| General task | Not applicable | Not applicable |

General tasks do not hold blocks and never use combinations.

---

## Migration checklist

- [ ] Increased intervals confirmed enabled for your tenant
- [ ] Property and Batch task creation with blocks moved to `create_with_combinations`
- [ ] Every `create_many`, `add_block`, `add_blocks`, and `update_block_workflow` call followed by `generate_block_combinations`
- [ ] `old_workflow_id` passed after every workflow swap
- [ ] At least 10 seconds between generation calls on the same task in your own loops
- [ ] `CombinationGenerationError` handled, with retries limited to `failed_blocks`
- [ ] Result-reading code matches on combination or child workflow ID, not `ROW#` interval ID
- [ ] Code paths for tenants without the feature still use `create`

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| A block shows no rows | Combinations were never generated | Call `generate_block_combinations` for the block |
| Old combinations remain after a workflow swap | `old_workflow_id` was not passed | Call `generate_block_combinations(old_workflow_id=<previous>)` |
| `create_with_combinations` rejects the task | Increased intervals is not enabled for the tenant | Use `create`, or ask your Albert representative to enable the feature |
| `TypeError` from a combination method | The task is a General task | Combinations apply to Property and Batch tasks only |
| Generation fails above 2,000 combinations | The block exceeds the cap | Add rules or overrides to reduce combinations |
| `parameter_setpoints` is empty on property data | Results are addressed by child workflow ID | Match through `interval_combination` |

If you run into any issues, please open a [GitHub issue](https://github.com/albert-labs/albert-python/issues).
