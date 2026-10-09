"""Turn an observed HTTP status into a verdict against an expected outcome.

Rules (SDK-216):

- A 5xx is always a finding, whatever was expected.
- Expected DENY passes only on 403 or 404; any 2xx is a leak.
- Expected ALLOW passes only on 2xx; 403/404 is an over-restriction.
- A 400 is inconclusive: the probe payload, not the ACL, may be wrong.
- For list/search paths, visibility is decided by canary presence, not status alone.
- UNDECIDED never passes or fails; it is reported for product.
"""

from dataclasses import dataclass
from enum import Enum

from tests.acl.contract.model import Expect


class Verdict(str, Enum):
    PASS = "pass"
    LEAK = "leak"
    OVER_RESTRICTED = "over_restricted"
    SERVER_ERROR = "server_error"
    INCONCLUSIVE = "inconclusive"
    UNDECIDED = "undecided"


DENY_STATUSES = frozenset({403, 404})


@dataclass(frozen=True)
class Observation:
    status: int
    canary_visible: bool | None = None


def judge(expect: Expect, obs: Observation) -> Verdict:
    if obs.status >= 500:
        return Verdict.SERVER_ERROR
    if expect is Expect.UNDECIDED:
        return Verdict.UNDECIDED
    if obs.status == 400 or (obs.status >= 400 and obs.status not in DENY_STATUSES):
        return Verdict.INCONCLUSIVE
    allowed = 200 <= obs.status < 300
    if allowed and obs.canary_visible is not None:
        allowed = obs.canary_visible
    if expect is Expect.ALLOW:
        return Verdict.PASS if allowed else Verdict.OVER_RESTRICTED
    return Verdict.LEAK if allowed else Verdict.PASS


FAILING = frozenset({Verdict.LEAK, Verdict.OVER_RESTRICTED, Verdict.SERVER_ERROR})
