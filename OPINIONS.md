# OPINIONS

Hard-won rules that aren't obvious from the code. Read before changing the things they name.

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

Why: callers (especially the Ask Albert agent) build partial update objects with
only the fields they want to change. Treating omitted fields as deletions emits
bad `delete` ops that the API rejects (e.g. "Delete operation not allowed for
attribute-name") or that silently wipe existing data (inventory rows, tags).

Regression tests: `test_update_partial_leaves_omitted_fields_untouched` (lots),
`test_update_partial_leaves_omitted_special_attrs_untouched` (tasks).
