"""Backwards-compatible re-export; the helper lives in ``tests.utils.wait``."""

from tests.utils.wait import poll_until

__all__ = ["poll_until"]
