import time
from collections.abc import Callable


def poll_until(
    fetch: Callable[[], list],
    *,
    predicate: Callable[[list], bool] | None = None,
    timeout: float = 30.0,
    interval: float = 1.0,
) -> list:
    """Poll ``fetch`` until the result satisfies ``predicate`` or the timeout elapses.

    Search-index-backed endpoints lag behind seeding; tests asserting on fresh
    seeds poll instead of assuming immediate visibility. With no ``predicate``,
    any non-empty result ends polling. Returns the last result.

    Pass a ``predicate`` when the assertion needs the complete expected set: a
    non-empty but partially indexed result satisfies the default check while
    remaining items are still becoming visible.
    """
    deadline = time.monotonic() + timeout
    while True:
        result = fetch()
        ready = predicate(result) if predicate is not None else bool(result)
        if ready or time.monotonic() >= deadline:
            return result
        time.sleep(interval)
