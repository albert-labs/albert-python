"""One call per check: observe, judge, record a report row, assert.

Failing verdicts stay red (no xfail). UNDECIDED skips with the product question.
"""

import pytest

from tests.acl.contract.model import UNDECIDED_REASON, Expect
from tests.acl.http import Response
from tests.acl.oracle import FAILING, Observation, Verdict, judge
from tests.acl.report import Row, record


def check(
    request: pytest.FixtureRequest,
    *,
    scenario: str,
    subject: str,
    action: str,
    expect: Expect,
    resp: Response,
    canary: str | None = None,
    detail: str = "",
) -> Verdict:
    visible = resp.contains(canary) if canary and 200 <= resp.status < 300 else None
    verdict = judge(expect, Observation(resp.status, visible))
    if verdict is Verdict.INCONCLUSIVE and not detail:
        detail = str(resp.body)[:200]
    record(
        request,
        Row(scenario, subject, action, expect.value, resp.status, verdict.value, detail),
    )
    if verdict is Verdict.UNDECIDED:
        pytest.skip(f"{UNDECIDED_REASON}: {detail or action}")
    assert verdict not in FAILING, (
        f"[{scenario}] {subject} {action}: expected {expect.value}, "
        f"got {resp.status} (canary visible={visible}) -> {verdict.value}"
    )
    assert verdict is not Verdict.INCONCLUSIVE, (
        f"[{scenario}] {subject} {action}: inconclusive {resp.status}: {detail}"
    )
    return verdict


def admin_control(admin_resp: Response, action: str, canary: str | None = None) -> None:
    """The admin must succeed; otherwise the probe is broken, not the ACL."""
    ok = 200 <= admin_resp.status < 300 and (canary is None or admin_resp.contains(canary))
    if not ok:
        pytest.fail(
            f"harness error: admin positive control failed for {action}: {admin_resp.status}",
            pytrace=False,
        )
