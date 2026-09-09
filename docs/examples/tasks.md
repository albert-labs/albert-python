# Tasks

Tasks in Albert Invent are a way to manage and track your daily work and collaborate with colleagues. There are three types of tasks: Batch Tasks, Property Tasks, and General Tasks.

## Intervals, Rules, and Overrides Overview

When designing experiments or testing formulations, scientists frequently vary one or more workflow parameters across discrete values. On [`PropertyTask`][albert.resources.tasks.PropertyTask] blocks, Albert Invent manages this matrix of conditions through **intervals**, **rules**, and **combination overrides**.

### What are intervals?

An **interval** is a discrete setpoint value assigned to a parameter within a workflow. When multiple parameters define intervals:

- **Cartesian Product**: Albert Invent computes all combinations of values across every intervalized parameter. For example, testing 3 temperatures (25 °C, 60 °C, 90 °C) and 2 stir speeds (500 RPM, 1500 RPM) creates \(3 \times 2 = 6\) experimental combinations.
- **Child Workflows**: Each combination materializes as an independent child workflow record (`WFL...`) linked to the task block.
- **Interval Barcodes**: Every combination receives a unique, persistent barcode (e.g. `OhI8ap0HY`) that remains stable across rule updates as long as the parameter setpoints are unchanged.

### Starting modes (`intervals_start_from`)

Each task block specifies an `intervals_start_from` strategy that controls the initial baseline before rules and overrides are applied:

- **Exclude Mode (`"all"`, default)**: Starts with the full Cartesian product (all combinations included). Rules and overrides prune out infeasible, unsafe, or unwanted combinations.
- **Include Mode (`"none"`)**: Starts with zero combinations (an empty set). Rules and overrides selectively pull in combinations, ideal for sparse screening or targeted Designs of Experiment (DoE).

### What are rules?

**Rules** dynamically evaluate combination variants against criteria defined on parameter values:

- **Conditions**: A condition compares a parameter against a threshold using operators (`=`, `!=`, `>`, `>=`, `<`, `<=`).
- **AND logic within a rule**: All conditions inside a single rule must match for that rule to trigger.
- **OR logic across rules**: If *any* rule triggers:
    - In **Exclude Mode** (`"all"`), the combination is excluded from the task.
    - In **Include Mode** (`"none"`), the combination is included in the task.

### What are overrides?

**Overrides** target a single, specific combination identified by its exact parameter values (e.g. Temperature = 100 °C and Speed = 2000 RPM):

- `skip`: Explicitly excludes the combination.
- `unskip`: Explicitly keeps or forces the inclusion of the combination.
- `is_manual=True`: In Include Mode, designates a manually cherry-picked combination.
- **Precedence**: Overrides are evaluated first and always take precedence over rules. For example, an `unskip` override guarantees a combination is retained even if an exclusion rule would otherwise drop it.

### Value-based helpers

While platform APIs require workflow-local internal IDs (`parameter_group_id`, `parameter_id`, and `row_id`), the Albert Python SDK provides value-based helpers on [`Workflow`][albert.resources.workflows.Workflow] so you can work entirely with human-readable parameter names and values:

- [`workflow.build_rule`][albert.resources.workflows.Workflow.build_rule]: Assembles a rule from single or compound condition criteria.
- [`workflow.build_exclusion_rule`][albert.resources.workflows.Workflow.build_exclusion_rule]: Semantic builder for Exclude Mode rules.
- [`workflow.build_inclusion_rule`][albert.resources.workflows.Workflow.build_inclusion_rule]: Semantic builder for Include Mode rules.
- [`workflow.build_rule_condition`][albert.resources.workflows.Workflow.build_rule_condition]: Resolves parameter name, operator, value, and unit into a [`RuleCondition`][albert.resources.interval_combinations.RuleCondition].
- [`workflow.build_override`][albert.resources.workflows.Workflow.build_override]: Generates a [`CombinationOverride`][albert.resources.interval_combinations.CombinationOverride] from a parameter-value dictionary.

---

## Create an intervalized Property task in Exclude Mode

When testing multiple formulation variants or process conditions, a Property Task can evaluate intervals across workflow parameters (such as temperature, speed, or concentration). Each combination of parameter setpoints materializes as a child workflow variant.

In **Exclude Mode** (`intervals_start_from="all"`, the default), combination generation starts with all possible Cartesian product variants included. You can define exclusion rules to filter out unwanted combinations (such as incompatible parameter settings) and overrides to force-include or force-skip specific variants.

!!! example "Create a Property Task with exclusion rules and overrides"
    ```python
    from albert import Albert
    from albert.resources.tasks import Block, PropertyTask

    client = Albert()

    # 1. Fetch an existing workflow containing intervalized parameters
    workflow = client.workflows.get_by_id(id="WFL456")

    # 2. Build rules and overrides using human-readable parameter names and values
    # Rule: Exclude all variants with both high heat and high speed
    rule = workflow.build_exclusion_rule(
        name="Exclude high heat with high speed",
        conditions=[
            ("Temperature", ">=", 90),
            ("Speed", ">=", 1500),
        ],
    )
    # Override: Skip a specific room-temperature/extreme-speed condition not caught by the general high-heat rule
    override = workflow.build_override(
        {"Temperature": 25, "Speed": 2000},
        action="skip",
    )

    # 3. Create the task with rules, overrides, and automatic combination generation
    task = client.tasks.create_with_combinations(
        task=PropertyTask(
            name="Adhesive Viscosity Screen",
            parent_id="PRO123",
            blocks=[
                Block(
                    data_template=[{"id": "DAT100"}],
                    workflow=[{"id": workflow.id}],
                    intervals_start_from="all",
                    rules=[rule],
                    overrides=[override],
                )
            ],
        ),
        wait=True,
    )

    # 4. Iterate over the materialized combinations
    block_id = task.blocks[0].id
    for combo in client.tasks.get_block_combinations(task_id=task.id, block_id=block_id):
        print(combo.id, combo.name, combo.interval_barcode)
    ```

!!! tip "Value-based helpers for rules and overrides"
    Rule conditions and combination overrides require workflow-local internal IDs (`parameter_group_id`, `parameter_id`, and `row_id`) that change when workflows are saved or updated.
    
    Instead of manually resolving internal IDs, use the helper methods on your [`Workflow`][albert.resources.workflows.Workflow] instance:
    
    - [`workflow.build_rule`][albert.resources.workflows.Workflow.build_rule]: Constructs an [`ExclusionRule`][albert.resources.interval_combinations.ExclusionRule] with human-readable conditions using tuples (e.g. `conditions=[("Temperature", ">=", 90)]`) or keyword arguments (`parameter="Temperature", operator=">=", value=90`).
    - [`workflow.build_exclusion_rule`][albert.resources.workflows.Workflow.build_exclusion_rule]: Semantic builder for Exclude Mode rules.
    - [`workflow.build_inclusion_rule`][albert.resources.workflows.Workflow.build_inclusion_rule]: Semantic builder for Include Mode rules.
    - [`workflow.build_rule_condition`][albert.resources.workflows.Workflow.build_rule_condition]: Constructs an individual [`RuleCondition`][albert.resources.interval_combinations.RuleCondition] with resolved group, parameter, and row IDs.
    - [`workflow.build_override`][albert.resources.workflows.Workflow.build_override]: Constructs a [`CombinationOverride`][albert.resources.interval_combinations.CombinationOverride] directly from a dictionary of parameter names and values (e.g. `workflow.build_override({"Temperature": 25, "Speed": 2000}, action="skip")`).

!!! warning "Property Tasks only"
    Child-workflow interval combinations are exclusively supported on [`PropertyTask`][albert.resources.tasks.PropertyTask]. They cannot be created or evaluated on [`BatchTask`][albert.resources.tasks.BatchTask] or [`GeneralTask`][albert.resources.tasks.GeneralTask].

!!! warning "Platform combinations cap"
    The platform enforces a maximum safety cap of 2,000 combinations per block. If your parameter intervals expand to more than 2,000 combinations (after applying rules and overrides), creation will fail.

!!! warning "Embedded combinations truncation"
    When a block contains 500 or more combinations, embedded combination lists on the task block payload are omitted to prevent payload bloat. Always use [`get_block_combinations`][albert.collections.tasks.TaskCollection.get_block_combinations] to iterate through combinations.

!!! note "Override precedence"
    Direct overrides always take precedence over rules:
    
    - `OverrideAction.SKIP`: Immediately excludes a combination, bypassing rules evaluation.
    - `OverrideAction.UNSKIP`: Immediately preserves a combination, even if an exclusion rule matches.

!!! note "Handling partial failures and retrying failed blocks"
    When `wait=True` is used, the task itself is created first on the platform before combination generation begins. If background generation fails on any block, the SDK raises `CombinationGenerationError`.
    
    Rather than re-creating the entire task (which would result in a duplicate task), inspect `err.task` and `err.failed_blocks`, and retry generation for only the failed blocks:
    
    ```python
    from albert.exceptions import CombinationGenerationError

    try:
        task = client.tasks.create_with_combinations(task=property_task, wait=True)
    except CombinationGenerationError as err:
        print(f"Task {err.task.id} was created, but combination jobs failed on: {err.failed_blocks}")
        for block_id in err.failed_blocks:
            client.tasks.generate_block_combinations(
                task_id=err.task.id,
                block_id=block_id,
                wait=True,
            )
    ```

!!! note "Asynchronous background generation"
    For large tasks with many blocks, you can pass `wait=False` to launch generation without blocking. Each block will contain `job_id` and `job_state` (such as `"submitted"` or `"in_progress"`), allowing your script to proceed or track job completion independently.

## Create an intervalized Property task in Include Mode

In **Include Mode** (`intervals_start_from="none"`), combination generation starts with *zero* active combinations. This mode is ideal for sparse designs of experiment (DoE) or targeted screening where you only want specific combinations evaluated.

In this mode:
- Rules act as **inclusion rules**: only combinations satisfying rule conditions are kept.
- Overrides with `action=OverrideAction.UNSKIP` and `is_manual=True` allow you to cherry-pick individual combinations into the task.

!!! example "Create a Property Task in Include Mode with manual overrides"
    ```python
    from albert import Albert
    from albert.resources.tasks import Block, PropertyTask

    client = Albert()

    workflow = client.workflows.get_by_id(id="WFL456")

    # 1. Define inclusion rule using workflow helper (low temperatures only)
    rule = workflow.build_inclusion_rule(
        name="Include low temperature variants",
        conditions=[
            ("Temperature", "<", 40),
        ],
    )

    # 2. Cherry-pick specific higher-temperature benchmark combinations
    # that would otherwise be omitted by the rule (Temperature < 40)
    override_1 = workflow.build_override(
        {"Temperature": 60, "Speed": 500},
        action="unskip",
        is_manual=True,
    )
    override_2 = workflow.build_override(
        {"Temperature": 90, "Speed": 1000},
        action="unskip",
        is_manual=True,
    )

    task = client.tasks.create_with_combinations(
        task=PropertyTask(
            name="Targeted Low-Temperature Screen",
            parent_id="PRO123",
            blocks=[
                Block(
                    data_template=[{"id": "DAT100"}],
                    workflow=[{"id": workflow.id}],
                    intervals_start_from="none",
                    rules=[rule],
                    overrides=[override_1, override_2],
                )
            ],
        ),
        wait=True,
    )

    combos = list(client.tasks.get_block_combinations(task_id=task.id, block_id=task.blocks[0].id))
    print(f"Materialized {len(combos)} combinations.")
    ```

!!! note "The `is_manual` flag"
    Setting `is_manual=True` on a [`CombinationOverride`][albert.resources.interval_combinations.CombinationOverride] is only valid when `intervals_start_from="none"`. It designates an override as an explicit manual addition to an otherwise empty set of combinations.

## Modify rules and regenerate combinations on an existing task

You can update rules and overrides on an existing task block at any time using [`set_block_rules`][albert.collections.tasks.TaskCollection.set_block_rules]. By default, the SDK automatically recalculates the Cartesian product and regenerates child-workflow combinations on Albert Invent.

!!! example "Update block rules and regenerate combinations"
    ```python
    from albert import Albert

    client = Albert()
    task_id = "TASFOR1"
    block_id = "BLK1"

    # 1. Inspect existing rules and overrides on the block
    current_rules = client.tasks.get_block_rules(task_id=task_id, block_id=block_id)
    print("Existing rules count:", len(current_rules.rules))
    print("Existing overrides count:", len(current_rules.overrides))

    # 2. Update the block with new rules (and clear previous overrides)
    # Fetch the block's current workflow to build rules using parameter names
    task = client.tasks.get_by_id(id=task_id)
    block = next(b for b in task.blocks if b.id == block_id)
    workflow = client.workflows.get_by_id(id=block.workflow[0].id)

    new_rule = workflow.build_exclusion_rule(
        name="Exclude cold temperatures",
        conditions=[
            ("Temperature", "<", 15),
        ],
    )

    # Combinations are regenerated automatically on Albert Invent by default
    updated_rules = client.tasks.set_block_rules(
        task_id=task_id,
        block_id=block_id,
        rules=[new_rule],
        overrides=[],  # Passing an empty list clears existing overrides
    )
    print("Regeneration status:", updated_rules.job.state)

    # 3. Read the updated combination variants
    updated_combos = list(client.tasks.get_block_combinations(task_id=task_id, block_id=block_id))
    print(f"Active combinations after rules update: {len(updated_combos)}")
    ```

!!! note "Automatic combination regeneration"
    [`set_block_rules`][albert.collections.tasks.TaskCollection.set_block_rules] automatically re-evaluates the Cartesian product and regenerates child-workflow combinations on the platform (`generate_combinations=True` by default). It automatically detects the block's current workflow and passes it as `old_workflow_id` so obsolete combinations are cleanly voided and unchanged barcodes are preserved.
    
    If you only wish to save rule definitions without immediately triggering background generation jobs, pass `generate_combinations=False`.

!!! note "Unset vs. empty convention"
    [`set_block_rules`][albert.collections.tasks.TaskCollection.set_block_rules] distinguishes between omitting a field and passing an empty list:
    
    - Omitting `rules` (or passing `rules=None`) leaves the block's existing rules untouched.
    - Passing `rules=[]` clears all existing rules on the block.
    - The same convention applies to `overrides`.

!!! note "Workflow replacement (swapping workflows)"
    If you swap a block's workflow using [`update_block_workflow`][albert.collections.tasks.TaskCollection.update_block_workflow], pass the **replaced** workflow ID as `old_workflow_id` when calling [`generate_block_combinations`][albert.collections.tasks.TaskCollection.generate_block_combinations] so the platform archives the old child workflows and provisions the new ones cleanly.

## Import results

This feature enables users to import a .csv file straight into the Data Template of a Property Task allowing them to easily mass enter results without having to type them in manually or copy-paste.

!!! example "Import results from a CSV file"
    ```python
    from albert import Albert
    from albert.resources.data_templates import ImportMode

    client = Albert.from_client_credentials()

    task = client.tasks.import_results(
        task_id="TAS123",
        inventory_id="INV123",
        data_template_id="DT123",
        file_path="path/to/results.csv",
        field_mapping={"comm": "Comments", "Solvent": " Solvent, ppm"},
        mode=ImportMode.CSV,
    )
    print(task)
    ```

!!! example "Import results using a script"
    ```python
    from albert import Albert
    from albert.resources.data_templates import ImportMode

    client = Albert.from_client_credentials()

    task = client.tasks.import_results(
        task_id="TAS123",
        inventory_id="INV123",
        data_template_id="DT123",
        block_id="BLK1",
        file_path="path/to/results.csv",
        mode=ImportMode.SCRIPT,
    )
    ```

!!! warning
    `import_results` deletes existing property data for the matching task/block/inventory/lot/interval
    before writing new values. Use with care if you need to preserve older results.
