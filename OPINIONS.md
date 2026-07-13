# OPINIONS

Hard-won rules that aren't obvious from the code. **Read the relevant section before
changing the things it names** — `AGENTS.md` points here for all non-obvious constraints.

## update() / PATCH payloads — unset is not empty

When writing or modifying any `update()` method or PATCH-payload generator
(`_generate_patch_payload`, `generate_adv_patch_payload`, or a collection-specific
variant):

**A field the caller never set must be left untouched.** Only a value the caller
explicitly provided participates in the diff.

- Gate the diff on `attribute in updated.model_fields_set`, never on `value is None`
  alone. An unset field defaults to `None` (or is coerced to `[]` by patterns like
  `getattr(updated, attr) or []`) and will otherwise be read as a deletion.
- Distinguish three states:
  - **unset** (`attribute not in model_fields_set`) -> no-op, leave server value.
  - **explicit `None`** -> delete the attribute.
  - **explicit `[]` / `{}`** -> clear to empty (an update, not a delete).
- Watch for `or []` / `or {}` coercions in special-case attribute loops
  (e.g. `inventory_information`, `tags`, `assigned_to`, `project` in tasks). They
  erase the unset-vs-empty distinction before the diff runs — guard with
  `model_fields_set` first.
- **Nested models need the same rule.** Top-level `update()` may gate on
  `updated.model_fields_set` (e.g. `cas` on `InventoryItem`), but optional fields
  on nested models must also be gated on `child.model_fields_set`. Required nested
  fields (e.g. `CasAmount.min`, `CasAmount.max`) are always set when the parent
  constructs the child, so diff those normally.
- **Check the backend contract** before emitting add/update/delete for a field. A
  field returned on GET is not necessarily patchable standalone (e.g.
  `substance_id` on inventory CAS: set on `casId` add, preserved on min/max
  update, removed only when the CAS entry is deleted — never via a `substanceId`
  delete op).
- Every `update()` docstring must have a `Notes` section listing patchable fields.
  Keep it in sync whenever a field is added to or removed from `updatable_attributes`
  or a collection-specific patch helper.

Why: callers build partial update objects with only the fields they want to change.
Treating omitted fields as deletions emits bad `delete` ops that the API rejects
(e.g. "delete not allowed for substanceId") or that silently wipe existing data
(inventory rows, tags).

Regression tests: `test_update_partial_leaves_omitted_fields_untouched` (lots),
`test_update_partial_leaves_omitted_special_attrs_untouched` (tasks),
`tests/utils/test_inventory_patches.py` (inventory CAS patch builder).

## Pagination — callers never see offset or limit

`AlbertPaginator` (`src/albert/core/pagination.py`) owns pagination state internally.

- **`offset` and `limit` are never public method parameters.** Do not add them to a
  collection method signature or docstring. Expose `max_items` as the only
  caller-facing control for early stopping.
- **KEY mode** (`PaginationMode.KEY`) uses `startKey` / `lastKey`. Do not pass
  `limit` from the SDK — the backend controls page size.
- **OFFSET mode** (`PaginationMode.OFFSET`) defaults to `limit=1000` internally and
  stops when `Items` is empty.

Why: exposing raw pagination params leaks backend details, invites misuse, and
diverges from the SDK's iterator-style API.

## Resource & search model naming

- When a search endpoint returns a different shape than the main resource, name the
  model `<Resource>SearchItem` (e.g. `ActivitySearchItem`, `UserSearchItem`).
- Never reuse the main resource model for search results when fields differ.
- Never name it `<Resource>Item` or anything else.
- Adding a **missing field** to an existing resource model is `fix`, not `feat` —
  the field already exists in the API response; the SDK was just incomplete.
  Reserve `feat` for new methods, parameters, or other caller-visible capabilities.

## Docstrings — caller-facing only

Docstrings describe **what** a method does from the caller's perspective. Never
mention internal implementation or backend specifics (diffing, patching, HTTP
methods, "returned by the API").

- Wrong: `"""Update an attachment by diffing the current server state."""`
- Right: `"""Update an attachment."""`
- Wrong: `The updated attachment returned by the API.`
- Right: `The updated Attachment.`

## Deprecations — method vs class

- **Method**: `@deprecated("... will be removed in 2.0. Use X instead.")` from
  `typing_extensions`. IDE strike-through and static-analysis warnings only.
- **Class**: `warnings.warn(..., DeprecationWarning, stacklevel=2)` in `__init__`.
  Fires a runtime warning at instantiation.
- Message format: `"thing() is deprecated and will be removed in 2.0. Use client.x.y() instead."`
- `@deprecated` alone does **not** emit a runtime `DeprecationWarning`.

## Releases & commits

- **Never bump the version manually.** Versions in `src/albert/__init__.py` and
  `pyproject.toml` are managed exclusively by release-please. PRs that touch either
  file will be flagged and must not be merged.
- `docs` is for documentation-only changes (AGENTS.md, docstrings, guides).
  `chore` is for maintenance (dependency bumps, CI, build tooling) — not doc edits.

## Testing — integration first, pure helpers excepted

- Prefer integration-style tests against the live API (requires
  `ALBERT_CLIENT_ID_SDK`, `ALBERT_CLIENT_SECRET_SDK`, `ALBERT_BASE_URL`).
- Do not add unit tests that use `FakeAlbertSession` to mock the API.
- Pure patch-payload builders and other side-effect-free helpers may have focused
  unit tests (e.g. `tests/utils/test_inventory_patches.py`) when they guard
  non-obvious diff behavior documented in this file.
