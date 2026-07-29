import time
from collections.abc import Callable


def poll_until(fetch: Callable[[], list], *, timeout: float = 30.0, interval: float = 1.0) -> list:
    """Poll ``fetch`` until it returns a non-empty result or the timeout elapses.

    Search-index-backed endpoints lag behind seeding; tests asserting on fresh
    seeds poll instead of assuming immediate visibility. Returns the last result.
    """
    deadline = time.monotonic() + timeout
    while True:
        result = fetch()
        if result or time.monotonic() >= deadline:
            return result
        time.sleep(interval)
