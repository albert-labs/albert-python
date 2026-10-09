# ACL suite (SDK-217, M1 likely scenarios)

Live, opt-in. Skipped unless `--run-acl` is passed. Never runs in CI.

```bash
export ALBERT_BASE_URL=https://app.albertinventdev.com
export ALBERT_ACL_ADMIN_TEST=<client_id>:<client_secret>   # admin userClass
export ALBERT_ACL_USERA_TEST=<client_id>:<client_secret>   # standard; role is swapped
export ALBERT_ACL_USERB_TEST=<client_id>:<client_secret>   # standard; fixed baseline role
uv run pytest tests/acl --run-acl
```

Output: `acl-report/acl-report.md` and `.csv`, with findings grouped by policy or FGC level.

## Rules

- **The backend is presumed wrong.** Expected values come only from policy names and
  descriptions (`contract/policies.py`), FGC level names and class semantics
  (`contract/fgc.py`), and product decisions on SDK-216. Never from backend code or a
  policy's operation list. `tests/unit/acl` enforces this with a lint.
- A failing check is a finding and stays red. Do not xfail, skip or loosen it. Strict
  xfail is allowed only after a ticket exists and product has accepted the gap.
- Undecided contract cells skip with `contract undecided: ask product` and are listed in
  the report.
- Verdicts (`oracle.py`):
  - 5xx is always a finding.
  - DENY passes only on 403/404.
  - On list/search paths, canary presence decides visibility.
  - 400 is inconclusive (a probe bug, not a finding).
- Every check runs an admin positive control first. If admin fails, it is a harness
  error, not a finding. Seed and identity problems raise `AclSetupError`.
- Each read path (get_by_id, list, bulk ids, search GET/POST, suggest, document search,
  llmsearch) is a separate action and report row. List paths use raw HTTP, never SDK
  `get_all`.

## Mechanics

- userA gets stable roles named `SDK-ACL-<label>`. They are created once and never
  mutated; a mismatch raises. userA's original role is restored at teardown. Clients use
  `retries=0` because the SDK retries 403 by default.
- The prod guard refuses prod URLs unless `ALBERT_ACL_ALLOW_PROD=1`.
- Preflight checks that there are three distinct users, that admin has userClass=admin,
  and that userA and userB are standard.
- All tests run in xdist group `acl`, because the role swap is global state.
