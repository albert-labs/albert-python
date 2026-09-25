from tests.integration.utils.wait import poll_until


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
    result = poll_until(lambda: [], timeout=0.01, interval=0.005)
    assert result == []
