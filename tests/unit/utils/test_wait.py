import json

import pytest
import requests

from albert.exceptions import InternalServerError
from tests.utils.wait import poll_until


def _make_server_error() -> InternalServerError:
    req = requests.PreparedRequest()
    req.method = "GET"
    req.url = "https://example.com/api/v3/x"
    req.body = None
    resp = requests.Response()
    resp.status_code = 500
    resp.reason = "Internal Server Error"
    resp.request = req
    resp._content = json.dumps({"errors": "transient failure"}).encode()
    resp.encoding = "utf-8"
    return InternalServerError(resp)


def test_poll_until_returns_first_non_empty_by_default():
    """Test that polling stops at the first non-empty result with no predicate."""
    calls = iter([[], ["a"], ["a", "b"]])
    assert poll_until(lambda: next(calls), interval=0) == ["a"]


def test_poll_until_predicate_waits_for_satisfaction():
    """Test that polling continues until the predicate accepts the result."""
    calls = iter([["a"], ["a", "b"], ["a", "b"]])
    result = poll_until(
        lambda: next(calls),
        predicate=lambda result: len(result) == 2,
        interval=0,
    )
    assert result == ["a", "b"]


def test_poll_until_returns_last_result_on_timeout():
    """Test that an unsatisfied predicate returns the last result after the timeout."""
    result = poll_until(lambda: [], predicate=lambda result: False, timeout=0.01, interval=0.005)
    assert result == []


def test_poll_until_returns_last_partial_result_on_timeout():
    """Test that a never-satisfied predicate returns the latest partial result."""
    partials = [["a"], ["a", "b"], ["a", "b", "c"]]
    calls = iter(partials)
    result = poll_until(
        lambda: next(calls, partials[-1]),
        predicate=lambda result: len(result) == 4,
        timeout=0.05,
        interval=0.01,
    )
    assert result == ["a", "b", "c"]


def test_poll_until_recovers_from_transient_fetch_error():
    """Test that a one-off AlbertServerError does not fail the poll."""
    outcomes = iter([_make_server_error(), ["a"]])

    def fetch():
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    assert poll_until(fetch, interval=0) == ["a"]


def test_poll_until_reraises_fetch_error_after_timeout():
    """Test that a fetch that always raises AlbertServerError propagates after the timeout."""

    def fetch():
        raise _make_server_error()

    with pytest.raises(InternalServerError):
        poll_until(fetch, timeout=0.01, interval=0.005)


def test_poll_until_does_not_catch_non_server_errors():
    """Test that non-AlbertServerError exceptions propagate immediately without polling."""
    calls = [0]

    def fetch():
        calls[0] += 1
        raise AttributeError("lambda typo")

    with pytest.raises(AttributeError, match="lambda typo"):
        poll_until(fetch, timeout=30.0, interval=0)

    assert calls[0] == 1
