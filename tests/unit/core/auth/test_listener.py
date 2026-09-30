"""Tests for the local SSO callback listener: port selection and request parsing.

``local_http_server`` binds a real loopback socket, but only ``bind``/``listen``/
``close`` (never ``connect``), so it runs fine under the offline network guard.
Feeding it a real HTTP request would require a client to *connect* to that
socket, which the guard blocks by design. So ``RequestHandler`` is exercised
directly here: a duck-typed fake request supplies the raw bytes a real socket
would have delivered, and ``do_GET`` runs unmodified against it.
"""

import io
import socket

import pytest

from albert.core.auth._listener import RequestHandler, _find_open_port, local_http_server


class _FakeRequest:
    """Duck-typed stand-in for a connected socket, feeding raw HTTP bytes in."""

    def __init__(self, raw: bytes) -> None:
        self._rfile = io.BytesIO(raw)
        self.sent = bytearray()

    def makefile(self, mode, *args, **kwargs):
        return self._rfile

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)

    def settimeout(self, timeout: float | None) -> None:
        pass


def _handle(raw_request: bytes):
    """Run RequestHandler.do_GET against raw request bytes and return (server, response)."""

    class _FakeServer:
        pass

    server = _FakeServer()
    request = _FakeRequest(raw_request)
    RequestHandler(request, ("127.0.0.1", 12345), server)
    return server, bytes(request.sent).decode()


# --- RequestHandler.do_GET --------------------------------------------------------


def test_do_get_captures_token_from_query_string():
    """Test that a token in the callback query string is captured on the server."""
    server, response = _handle(b"GET /?token=abc123 HTTP/1.1\r\nHost: localhost\r\n\r\n")

    assert server.token == "abc123"
    assert "200 OK" in response
    assert "Authentication successful" in response


def test_do_get_sets_none_token_when_missing():
    """Test that a callback with no token query param sets server.token to None."""
    server, response = _handle(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")

    assert server.token is None
    assert "Authentication failed (no token found)" in response


def test_do_get_sends_restrictive_content_security_policy():
    """Test that the callback response includes a locked-down CSP header."""
    _, response = _handle(b"GET /?token=abc123 HTTP/1.1\r\nHost: localhost\r\n\r\n")

    assert "Content-Security-Policy: default-src 'none'; frame-ancestors 'none'" in response


def test_do_get_takes_first_token_when_repeated():
    """Test that a repeated token query param uses the first occurrence."""
    server, _ = _handle(b"GET /?token=first&token=second HTTP/1.1\r\nHost: localhost\r\n\r\n")

    assert server.token == "first"


# --- _find_open_port ---------------------------------------------------------------


def test_find_open_port_returns_a_bindable_port():
    """Test that _find_open_port returns a port number that can actually be bound."""
    port = _find_open_port(start=51000, stop=51010)

    assert port is not None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))  # does not raise


def test_find_open_port_returns_none_for_empty_range():
    """Test that an empty port range (start == stop) returns None without trying to bind."""
    assert _find_open_port(start=51100, stop=51100) is None


def test_find_open_port_skips_an_occupied_port():
    """Test that a port already bound elsewhere is skipped in favor of the next one."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen(1)
        occupied_port = occupied.getsockname()[1]

        found = _find_open_port(start=occupied_port, stop=occupied_port + 5)

        assert found is not None
        assert found != occupied_port


# --- local_http_server context manager ----------------------------------------------


def test_local_http_server_yields_server_and_port():
    """Test that the context manager yields a fresh server with no token and the right timeout."""
    with local_http_server(timeout=3, minimum_port=51200, maximum_port=51210) as (server, port):
        assert server.token is None
        assert server.timeout == 3
        assert 51200 <= port < 51210


def test_local_http_server_closes_socket_on_normal_exit():
    """Test that the server's socket is closed once the with-block exits normally."""
    with local_http_server(timeout=1, minimum_port=51300, maximum_port=51310) as (server, _port):
        pass

    assert server.socket.fileno() == -1


def test_local_http_server_closes_socket_even_on_exception():
    """Test that the server's socket is still closed if the with-block raises."""
    holder: dict[str, object] = {}

    with (
        pytest.raises(ValueError, match="boom"),
        local_http_server(timeout=1, minimum_port=51400, maximum_port=51410) as (server, _p),
    ):
        holder["server"] = server
        raise ValueError("boom")

    assert holder["server"].socket.fileno() == -1


def test_local_http_server_raises_runtime_error_when_no_port_available(
    monkeypatch: pytest.MonkeyPatch,
):
    """Test that exhausting the port range raises a clear RuntimeError."""
    monkeypatch.setattr(
        "albert.core.auth._listener._find_open_port", lambda *, start, stop=None: None
    )

    with (
        pytest.raises(RuntimeError, match="No open port found"),
        local_http_server(timeout=1, minimum_port=51500),
    ):
        pass
