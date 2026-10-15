"""Accepted platform limitations: checks that are expected to fail until the platform can
enforce them. Non-strict, so a case that happens to pass reports XPASS instead of failing.
"""

import pytest

LOT_GET_INHERITANCE = pytest.mark.xfail(
    reason="lot reads don't inherit the inventory's (or its project's) access; accepted "
    "platform limitation",
    strict=False,
)
