import socket
from collections.abc import Generator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

LOCALHOST = "127.0.0.1"
DEFAULT_PORTS_TO_TRY = 100


def _find_open_port(*, start: int, stop: int | None = None) -> int | None:
    stop = stop or start + DEFAULT_PORTS_TO_TRY
    for port in range(start, stop):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((LOCALHOST, port))
                sock.listen(1)
                return port
        except OSError:
            continue
    return None


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.token = None
        parsed = urlparse(self.path)
        query_str = parse_qs(parsed.query)
        self.server.token = query_str.get("token", [None])[0]

        status = "successful" if self.server.token else "failed (no token found)"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            f"""
            <html>
            <body>
                <h1>Authentication {status}</h1>
                <p>You can close this window now.</p>
                <script>window.close()</script>
                <button onclick="window.close()">Close Window</button>
            </body>
            </html>
            """.encode()
        )

    def log_message(self, format, *args):
        # suppress standard logging
        pass


@contextmanager
def local_http_server(
    *,
    timeout: int,
    minimum_port: int = 5000,
    maximum_port: int | None = None,
    handler: type[BaseHTTPRequestHandler] = RequestHandler,
) -> Generator[tuple[HTTPServer, int], None, None]:
    port = _find_open_port(start=minimum_port, stop=maximum_port)
    if port is None:
        raise RuntimeError(
            f"No open port found in range {minimum_port}-{minimum_port + DEFAULT_PORTS_TO_TRY}"
        )

    server = HTTPServer((LOCALHOST, port), handler)
    server.allow_reuse_address = True
    server.token = None
    server.timeout = timeout

    try:
        yield server, port
    finally:
        server.server_close()
