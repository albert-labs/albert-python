"""Fixtures and guards for the offline unit suite.

Unit tests never touch the network or read credentials. The autouse guards below
enforce that mechanically; see ``tests/unit/TESTING.md``.
"""

import os
import socket

import pytest

from albert.core.session import AlbertSession

UNIT_BASE_URL = "https://unit.test"


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any real outbound connection.

    ``responses`` and ``respx`` intercept requests before a socket opens, so
    sanctioned HTTP fakes keep working.
    """

    def guard(self: socket.socket, *args, **kwargs):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError(
                "Unit tests must not open network connections. "
                "Use `responses`/`respx` (see tests/unit/TESTING.md) or move the test "
                "to tests/integration."
            )
        return real_connect(self, *args, **kwargs)

    real_connect = socket.socket.connect
    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket.socket, "connect_ex", guard)


@pytest.fixture(autouse=True)
def _strip_albert_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove ``ALBERT_*`` env vars so no unit test depends on ``.env`` credentials."""
    for key in list(os.environ):
        if key.startswith("ALBERT_"):
            monkeypatch.delenv(key)


@pytest.fixture
def offline_session() -> AlbertSession:
    """An ``AlbertSession`` with a static token and a non-routable base URL.

    Use it to construct a collection when testing its private pure helpers, or pair
    it with ``responses`` to test request shape.
    """
    return AlbertSession(base_url=UNIT_BASE_URL, token="unit-token")
