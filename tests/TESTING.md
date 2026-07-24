# Writing Integration Tests

The integration suite runs **in parallel** with pytest-xdist (`-n 4` in CI, `--dist loadgroup`
via `addopts` in `pyproject.toml`). Every rule in this document exists to keep tests correct
and flake-free under that model. New tests must follow these patterns; a test that passes
sequentially but races other workers will fail intermittently in CI and is considered broken.

## How the parallel model works

- Each xdist worker is a separate process with its **own copy of every session-scoped fixture**.
- `seed_prefix` is a per-worker `SDK-Test-<uuid>` string. All seeded entity names include it,
  so workers never collide on names.
- `--dist loadgroup` assigns tests to workers by their `xdist_group` mark. All tests in one
  group run on one worker, so they share one set of session fixtures.
- Tests **without** a group mark are scheduled one by one onto any free worker. Two tests from
  the same unmarked file can land on different workers, and each worker will build its own copy
  of every session fixture those tests request.
- Workers finish at different times. When a worker finishes, its session fixture teardowns
  **delete its seeded entities while other workers are still running tests**.

That last point drives most of the rules below.

## Rule 1: assign the right xdist group

Any test file that uses a session-scoped `seeded_*` or expensive `static_*` fixture must carry
a module-level mark:

```python
pytestmark = pytest.mark.xdist_group("datatemplates")
```

Pick the group whose worker already builds the fixtures you need:

| Group | Owns fixture chain | Files (non-exhaustive) |
|---|---|---|
| `tasks` | `seeded_tasks` and everything under it (`seeded_workflows`, `seeded_notes`, `seeded_links`, `seeded_reports`) | test_tasks, test_batch_data, test_property_data, test_notes, test_links, test_reports, test_workflows |
| `sheets` | `seeded_worksheet`, `seeded_sheet`, `seeded_products` | test_worksheet, test_product_design, resources/test_sheets |
| `inventory` | `seeded_inventory`, `seeded_lots`, `seeded_pricings`, `seeded_label_templates` | test_inventory, test_attachments, test_lots, test_pricings, test_label_templates |
| `datatemplates` | `seeded_data_templates`, `seeded_data_columns`, `seeded_units`, `seeded_parameters`, `seeded_parameter_groups`, `seeded_targets`, `seeded_smart_dataset` | test_data_templates, test_data_columns, test_units, test_parameters, test_parameter_groups, test_targets, test_smart_datasets, test_design_runs |
| `projects` | `seeded_projects`, `seeded_locations`, `seeded_storage_locations`, `seeded_cas`, `seeded_companies`, `seeded_notebooks` | test_projects, test_notebooks, test_locations, test_storage_locations, test_cas, test_company |
| `bt` | `seeded_btdataset`, `seeded_btmodelsession`, `seeded_btmodel`, `seeded_btinsight` | test_btdataset, test_btmodel, test_btinsight |
| `entitytypes`, `teams`, `tags`, `customtemplates`, `lists`, `customfields` | one small fixture family each | the matching single file |

Guidelines:

- **New test file for an existing collection**: use the group that already owns its fixtures.
- **New fixture family with no dependency on existing chains**: create a new group named after
  the module (like `teams` or `bt`). One group per independent family.
- **File uses only `client` / `fake_client` / function-scoped fixtures**: leave it unmarked so
  the scheduler can balance it freely. The moment it grows a `seeded_*` dependency, add a mark.
- Never split one file across groups; `pytestmark` applies to the whole module. If two tests in
  one file genuinely need different heavy chains, that is a sign they belong in different files.
- Group assignment affects wall time: the `tasks` worker is the critical path. Do not add
  slow tests to `tasks` if another group's fixtures suffice.

## Rule 2: treat shared seeded fixtures as read-only

Session fixtures (`seeded_tags`, `seeded_locations`, ...) are shared by every test on the
worker, and their list order matters (seeding helpers index into them).

- Never delete, rename, or update an entity owned by a `seeded_*` fixture.
- A test that exercises update/delete creates its **own private entity** and cleans it up in
  `try/finally`, suppressing `NotFoundError`:

```python
def test_tag_update(client: Albert):
    test_tag = client.tags.create(tag=Tag(tag=f"TEST - rename me {uuid.uuid4()}"))
    try:
        ...asserts...
    finally:
        with suppress(NotFoundError):
            client.tags.delete(id=test_tag.id)
```

- Name private entities with `seed_prefix` or `TEST - <uuid>` so leaked entities are
  identifiable and never collide across workers.

## Rule 3: never assert on unscoped search results

`text=` and `name=` search parameters are **tokenized full-text queries**, not prefix or
substring filters. `text=seed_prefix` still matches unrelated old records (tokens like "SDK"
and "Test"), including entities the client cannot read (ACL 403) or that another worker just
deleted. The search index also lags writes by seconds.

For any search-based assertion:

1. Scope the query with `text=`/`name=` set to `seed_prefix` (reduces noise).
2. **Filter results to the ids owned by the fixture** (correctness).
3. Wrap the fetch in `poll_until` from `tests/utils/wait.py` (index lag).

```python
from tests.utils.wait import poll_until

def test_hydrate_project(client: Albert, seed_prefix: str, seeded_projects: list[Project]):
    seeded_ids = {p.id for p in seeded_projects}
    projects = poll_until(
        lambda: [
            p
            for p in client.projects.search(text=seed_prefix, max_items=100)
            if p.id in seeded_ids
        ]
    )
    assert projects, "Expected at least one project in search results"
```

Also:

- Never assert **exact counts** of unscoped `search()`/`get_all()` results; other workers
  create and delete entities concurrently. Count only your own fixture's ids, or better, skip
  the search round-trip and use the fixture directly (see `test_get_by_ids`).
- Hydrating or `get_by_id`-ing an entity you did not seed can 403/404 at any moment.
- Watch id formats: inventory search items drop the `INV` prefix, so compare with
  `f"INV{item.id}"`.

## Rule 4: seeding conventions (conftest.py / seeding.py)

- Seed data generators live in `tests/seeding.py`; every generated name embeds `seed_prefix`.
- Fixtures create entities concurrently through `_pmap` (order-preserving, retries once on
  5xx because urllib3 does not retry POSTs) and tear down through `_delete_all`.
- **Append** new seed entities at the end of a generator's list. Tests and other seeders index
  into these lists (`seeded_locations[2]`), so reordering or removing entries breaks them.
- Shared, non-prefixed static entities (`static_custom_fields`, `static_lists`) must be
  registered **sequentially** through `_get_or_register`: concurrent same-name creates from
  multiple workers 504 the backend. The `entitytypes` endpoint 500s under concurrent creates,
  so `seeded_entity_types` also stays sequential.
- The fixed `time.sleep(1.5)` / `time.sleep(3)` calls after seeding are deliberate
  search-index buffers. Do not remove them; in tests, prefer `poll_until` over new sleeps.

## Rule 5: general hygiene

- Integration tests only; no unit tests with `FakeAlbertSession`.
- Docstrings crisp, start with "Test ...".
- The shared `client` is session-scoped and used from multiple threads during seeding; do not
  add fixture code that mutates client/session state.
- Env vars required: `ALBERT_CLIENT_ID_SDK`, `ALBERT_CLIENT_SECRET_SDK`, `ALBERT_BASE_URL`.

## Running

```bash
uv run pytest tests -n 4          # parallel, same as CI (loadgroup comes from addopts)
uv run pytest tests/collections/test_tags.py -v   # single file, sequential
```

Before opening a PR that touches fixtures or adds tests to a group, run at least the affected
group's files with `-n 4` to catch cross-worker races.

## Checklist for a new test file

- [ ] `pytestmark = pytest.mark.xdist_group("...")` chosen per Rule 1 (or deliberately unmarked because only `client` is used)
- [ ] No mutation of `seeded_*` entities; private entities cleaned up in `try/finally`
- [ ] Search assertions scoped, id-filtered, and wrapped in `poll_until`
- [ ] No exact-count asserts on global queries
- [ ] Names of created entities include `seed_prefix` or `TEST - <uuid>`
- [ ] Ran the file plus its group with `-n 4` locally
