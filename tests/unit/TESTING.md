# Writing Unit Tests

Start at [`tests/TESTING.md`](../TESTING.md) to decide whether a test is unit or integration.
This guide covers `tests/unit/` only.

Unit tests check logic the SDK owns. They run offline, in about two seconds, on every PR
before the integration suite. A unit test earns its place only if it **fails when the logic
it covers breaks**; a test that would still pass against a stubbed-out function is cut.

## Layout: mirror `src/albert/`

```
tests/unit/
├── conftest.py        guards + offline_session (autouse guards apply to every unit test)
├── core/              src/albert/core/          (core/shared/, core/auth/)
├── utils/             src/albert/utils/
├── resources/         src/albert/resources/     validators, serializers, model tolerance
├── collections/       src/albert/collections/   private pure helpers ONLY
├── meta/              repo-wide static checks (docstrings, public signatures)
└── test_exceptions.py src/albert/exceptions.py
```

- `src/albert/utils/tasks.py` → `tests/unit/utils/test_tasks.py`. One file per source module;
  split into topical files (`test_tasks_csv.py`) only past about 600 lines.
- No `xdist_group` marks. Unit tests share no state and schedule freely.
- Every directory has an `__init__.py` (unit and integration trees share basenames).

## What a unit test must never do

The conftest guards enforce the first two mechanically:

- **Open a network connection.** `_block_network` raises on any real `connect`.
- **Read credentials or `.env`.** `_strip_albert_env` removes every `ALBERT_*` variable.
- **Import from `tests/integration/`** (`client`, `seeded_*`, `static_*`, `seed_prefix`,
  `poll_until`, `seeding`).
- **Encode assumed server behavior.** A fake response may be shaped like a real one, but the
  assertion is about what the SDK sends or how it reacts, never "the API returns X".
- **Assert trivia.** That a Pydantic field exists, that a default is `None`, that a
  constructor stores its argument.

## What to test

### Patch / diff builders (highest priority)

`update()` correctness lives in these builders, and a wrong op silently wipes customer data
(see `OPINIONS.md`, "update() / PATCH payloads"). Cover this matrix for every builder, for
each attribute family it special-cases (scalars, lists, metadata, tags, ACLs, nested models):

| Caller state on `updated` | Expected |
|---|---|
| field **unset** (not in `model_fields_set`) | no op |
| field explicitly `None` | `delete` op, or no op if the attribute is non-deletable |
| field explicitly `[]` / `{}` | clear (an update/delete of each existing entry, never a no op) |
| field changed | `update` (or `add`) with the correct `old_value` |
| field unchanged | no op |
| nested optional field unset on the child model | no op for that child field |

Build partial `updated` objects the way a caller does (`Model(id=..., only_the_field=...)`),
not with `model_copy(update=...)` from `existing`, so `model_fields_set` matches real use.
When a model's required field must be `None`, use `Model.model_construct(...)`.

Assert on the full list of ops (attribute, operation, values), not only its length.

### Pure transforms (`src/albert/utils/`)

Deterministic functions: exercise each branch with small, readable inputs. Use
`pytest.mark.parametrize` for input tables. For DataFrame helpers, build the frame inline.

### Resource models (`src/albert/resources/`)

- Validators and serializers: the accept, reject (`pytest.raises(ValidationError)`), and
  coerce paths of each `field_validator` / `model_validator` / serializer.
- Wire format: `model_dump(by_alias=True, mode="json", exclude_none=True)` produces the
  camelCase shape, and `model_validate` of that shape round-trips.
- Tolerance: realistic API payload quirks (missing optional keys, `[{}]` links, unknown enum
  strings) parse instead of raising.

### Collection private helpers (`tests/unit/collections/`)

Only `_`-prefixed / `@staticmethod` helpers with no I/O. Construct the collection with the
`offline_session` fixture (static token, non-routable base URL); no request is made:

```python
from albert.collections.lots import LotCollection
from albert.resources.lots import Lot


def test_unset_fields_emit_no_ops(offline_session):
    """Test that fields the caller never set produce no patch operations."""
    existing = Lot(id="LOT1", inventory_id="INV1", inventory_on_hand=5, notes="old")
    updated = Lot(id="LOT1", inventory_id="INV1", inventory_on_hand=5)

    payload = LotCollection(session=offline_session)._generate_lots_patch_payload(
        existing=existing, updated=updated
    )

    assert payload.data == []
```

Do **not** unit-test public collection methods; integration covers them. If a public method
holds branching logic you want to test, extract it into a pure helper first (a pure move,
no behavior change, in its own commit) and test the helper.

### Core plumbing with HTTP fakes (`tests/unit/core/`)

Session, auth, and exception mapping need a response to react to. Use the transport-level
fakes, which let the real `AlbertSession` / `AsyncAlbertSession` code run:

- `responses` for the sync session (`requests`).
- `respx` for the async session (`httpx`).

These are the only sanctioned HTTP fakes. Do not hand-roll a fake `requests.Session`.
Duck-typed stubs of a narrower interface are fine where the code under test only needs that
interface (e.g. `_ScriptedSession` in `core/test_pagination.py` feeds pages to a paginator).

```python
import pytest
import responses

from albert.exceptions import NotFoundError
from tests.unit.conftest import UNIT_BASE_URL


@responses.activate
def test_404_maps_to_not_found(offline_session):
    """Test that a 404 response raises NotFoundError."""
    responses.get(f"{UNIT_BASE_URL}/api/v3/x/1", status=404, json={"message": "nope"})

    with pytest.raises(NotFoundError):
        offline_session.get("/api/v3/x/1")
```

Assert on **what the SDK sends** (method, URL, query, headers, JSON body via
`json.loads(responses.calls[0].request.body)`) and **how it reacts** (raises, returns,
refreshes a token, retries). Keep each fake to the minimum response the code path needs.

### Meta checks (`tests/unit/meta/`)

Static guarantees over the whole codebase that turn `AGENTS.md` / `OPINIONS.md` rules into
failures: attribute docstrings on resource fields, keyword-only public methods, `max_items`
defaulting to `None`, no `offset`/`limit` in public signatures, no Sphinx roles or em dashes
in docstrings. Add one when a rule is mechanically checkable and has been broken before.

## When you change SDK code

- New or changed branching logic in a collection goes into a pure helper with unit tests in
  the same PR.
- Fixing a bug in a patch builder, transform, or validator: add the failing case as a unit
  test first.
- Adding a resource validator: add its accept/reject/coerce cases.

## Running

```bash
uv run pytest tests/unit
uv run pytest tests/unit --cov --cov-report=term-missing   # see untested lines
```

Use `--cov` (source comes from `pyproject.toml`) or `--cov=albert`. A dotted submodule target
such as `--cov=albert.utils.tasks` fails with `numpy: cannot load module more than once per
process`; read the per-file row from the package-level report instead.

## Checklist

- [ ] File mirrors the source module path; directory has `__init__.py`
- [ ] No imports from `tests/integration/`; no env vars; no real network
- [ ] Patch builders cover the full unset / `None` / `[]` / changed / unchanged matrix
- [ ] HTTP fakes only via `responses` / `respx`, asserting on request shape or SDK reaction
- [ ] Each test fails if the covered logic is broken (try it: break the code, see red)
- [ ] Docstrings start with "Test ..."
