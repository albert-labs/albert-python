"""Live policy catalog must match the contract (names and descriptions, verbatim)."""

import pytest

from albert import Albert
from tests.acl.contract.policies import BY_ID, REQUIRED_IDS
from tests.acl.http import call
from tests.acl.report import Row, record


@pytest.fixture(scope="module")
def live_policies(admin: Albert) -> dict[str, dict]:
    resp = call(admin, "GET", "/api/v3/acl/policies")
    assert resp.status == 200, f"getPolicies failed: {resp.status}"
    body = resp.body
    items = body[0].get("Items") if isinstance(body, list) and body else resp.items()
    return {p["id"]: p for p in items or []}


def test_every_contracted_policy_exists(request, live_policies):
    """Test that every required contract policy is present in the live catalog."""
    missing = sorted(REQUIRED_IDS - live_policies.keys())
    for pid in missing:
        record(request, Row("policy_contract", pid, "exists", "allow", None, "leak", "missing"))
    assert not missing, f"policies missing from tenant: {missing}"


def test_no_uncontracted_policies(request, live_policies):
    """Test that the tenant exposes no policy the contract does not describe."""
    extra = sorted(live_policies.keys() - BY_ID.keys())
    for pid in extra:
        record(request, Row("policy_contract", pid, "uncontracted", "deny", None, "leak", ""))
    assert not extra, f"policies with no contract entry (add a hand-written contract): {extra}"


@pytest.mark.parametrize("policy_id", sorted(BY_ID))
def test_policy_text_matches_contract(request, live_policies, policy_id):
    """Test that a policy's live name and description match the contract verbatim."""
    contract = BY_ID[policy_id]
    live = live_policies.get(policy_id)
    if live is None:
        if contract.optional:
            pytest.skip(f"{policy_id} is optional (dev-only) and absent")
        pytest.fail(f"{policy_id} missing")
    drift = []
    if live.get("name") != contract.name:
        drift.append(f"name {live.get('name')!r} != {contract.name!r}")
    if live.get("description") != contract.description:
        drift.append(f"description {live.get('description')!r} != {contract.description!r}")
    if drift:
        record(
            request,
            Row("policy_contract", policy_id, "text", "match", None, "leak", "; ".join(drift)),
        )
    assert not drift, f"{policy_id}: policy text drifted; re-derive contract by hand: {drift}"
