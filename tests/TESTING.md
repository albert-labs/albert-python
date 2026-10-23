# Testing

Read this before writing or changing any test. It decides **which suite** a test belongs to;
each suite has its own guide with the binding rules.

| Suite | Guide | Runs | Needs |
|---|---|---|---|
| `tests/unit/` | [`unit/TESTING.md`](unit/TESTING.md) | every PR, first, in about 2s | nothing (no env, no network) |
| `tests/integration/` | [`integration/TESTING.md`](integration/TESTING.md) | every PR, after unit | `ALBERT_CLIENT_ID_SDK`, `ALBERT_CLIENT_SECRET_SDK`, `ALBERT_BASE_URL` |

Integration tests are the primary mechanism: the SDK is a thin client over the Albert API,
and only a live call proves the API accepts what we send and returns what we parse.

## Unit or integration?

Ask: **is the thing being checked owned by the SDK, or by the backend?**

- **Unit**: logic whose output is fully determined by its inputs.
  - Patch/diff builders (`_generate_*_patch_payload`, `utils/_patch.py`, `utils/inventory.py`).
  - Pagination engine behavior (`has_more`, `total`, `max_items`, key vs offset).
  - Pure transforms in `src/albert/utils/`.
  - Resource model validators, serializers, alias round-trips.
  - Session and auth plumbing: header handling, query encoding, how a response status maps
    to an exception, token refresh. Uses an HTTP fake (see the unit guide).
  - Repo-wide static guarantees (`tests/unit/meta/`).
- **Integration**: anything whose correctness depends on server behavior.
  - Public collection methods end to end (`create`, `get_by_id`, `search`, `update`, ...).
  - Whether the API accepts a payload, what it returns, search/index semantics, ACLs.

If you would need to invent a server response to make the test meaningful, it is an
integration test. Never mock the API to "prove" server behavior.

Public collection methods are covered by integration tests. When a collection method grows
branching logic on caller input (payload assembly, diffing, validation, batching), put that
logic in a pure helper and unit-test the helper (see the unit guide).

## Running

```bash
uv run pytest tests/unit                      # offline, fast
uv run pytest tests/integration -n 4          # live, parallel (same as CI)
uv run pytest tests/unit/utils/test_tasks.py -v
uv run pytest                                 # everything
```

## Shared conventions

- Test docstrings are crisp and start with "Test ...", describing behavior, not implementation.
- Test files are named `test_<module>.py` after the source module they cover.
- Shared test data files live in `tests/data/`.
