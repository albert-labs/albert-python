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

`AlbertPaginator` owns all pagination state internally. `offset` and `limit` are
never public method parameters; `max_items` is the only caller-facing control.

Why: exposing raw pagination params leaks backend details, invites misuse, and
diverges from the SDK's iterator-style API.

## Paginators — override _response_items for non-standard response keys

`AlbertPaginator._response_items` defaults to reading `data["Items"]` or
`data["items"]`. If an endpoint returns its list under any other key (e.g.
`substances`, `results`, `data`), you **must** override `_response_items` in the
paginator subclass. Forgetting this makes every page look empty and iteration
stops immediately after the first response.

## max_items — always default to None in search methods

Never set a non-`None` default for `max_items` on a `search()` method. A fixed
default silently truncates results for callers writing `for x in client.foo.search(...)`
expecting all matches, with no indication more exist unless they inspect `has_more`.
The SDK convention is `max_items: int | None = None` (unbounded by default).

Why: `substances_v4.search()` shipped with `max_items=100`, silently capping every
search at 100 results. Fixed in commit fa639977.

## Resource & search model naming

- When a search endpoint returns a different shape than the main resource, name the
  model `<Resource>SearchItem` (e.g. `ActivitySearchItem`, `UserSearchItem`).
- Never reuse the main resource model for search results when fields differ.
- Never name it `<Resource>Item` or anything else.
- Adding a **missing field** to an existing resource model is `fix`, not `feat` —
  the field already exists in the API response; the SDK was just incomplete.
  Reserve `feat` for new methods, parameters, or other caller-visible capabilities.

## Deprecations — @deprecated does not emit a runtime warning

`@deprecated` from `typing_extensions` gives IDE strike-through and static-analysis
warnings only. It does **not** fire a `DeprecationWarning` at runtime. For class
deprecations that need a runtime warning at instantiation (e.g. `CasCollection`),
use `warnings.warn(..., DeprecationWarning, stacklevel=2)` in `__init__` as well.

## Releases — docs vs chore commit type

`docs` is for documentation-only changes (AGENTS.md, OPINIONS.md, docstrings, guides).
`chore` is for maintenance (dependency bumps, CI, build tooling) — not doc edits.

Why: release-please uses commit types to determine changelog entries. Mislabeling a
doc improvement as `chore` buries it; mislabeling a build change as `docs` creates a
spurious changelog section.

## Testing — when unit tests are acceptable

Prefer integration-style tests against the live API. Do not add unit tests that mock
the API with `FakeAlbertSession`.

Exception: pure patch-payload builders and other side-effect-free helpers (e.g.
`_generate_patch_payload`) may have focused unit tests when they guard non-obvious
diff behavior — the same helpers documented in the `update()` section above. These
are the cases where a unit test gives real signal because there is no I/O to fake.
