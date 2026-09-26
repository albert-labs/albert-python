import pytest

from tests.utils.wait import poll_until


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
    """Test that a one-off fetch exception does not fail the poll."""
    outcomes = iter([RuntimeError("transient 503"), ["a"]])

    def fetch():
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    assert poll_until(fetch, interval=0) == ["a"]


def test_poll_until_reraises_fetch_error_after_timeout():
    """Test that a fetch that always raises propagates the exception after the timeout."""

    def fetch():
        raise RuntimeError("persistent 503")

    with pytest.raises(RuntimeError, match="persistent 503"):
        poll_until(fetch, timeout=0.01, interval=0.005)
