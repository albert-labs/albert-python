"""Raw HTTP probes that return the status instead of raising.

ACL tests must see the exact status code, so they call the session directly rather
than SDK collection methods (SDK ``get_all`` on several collections hydrates through
``/search`` + ``get_by_id`` and would mix read paths).
"""

from dataclasses import dataclass
from typing import Any

from albert import Albert
from albert.exceptions import AlbertHTTPError


@dataclass
class Response:
    status: int
    body: Any

    def items(self) -> list:
        body = self.body
        if isinstance(body, list):
            return body
        if isinstance(body, dict):
            for key in ("Items", "items", "data"):
                if isinstance(body.get(key), list):
                    return body[key]
        return []

    def contains(self, token: str) -> bool:
        """Whether ``token`` (an id or canary) appears anywhere in the body."""
        return token in repr(self.body)


def call(client: Albert, method: str, path: str, **kwargs) -> Response:
    try:
        resp = client.session.request(method, path, **kwargs)
    except AlbertHTTPError as err:
        resp = err.response
        if resp is None:
            raise
    try:
        body = resp.json() if resp.content else None
    except ValueError:
        body = resp.text
    return Response(status=resp.status_code, body=body)


def call_all_pages(
    client: Albert, method: str, path: str, *, token: str, params: dict | None = None, **kwargs
) -> Response:
    """Follow ``lastKey`` until ``token`` appears or the listing ends.

    A non-2xx page is returned as-is so denials keep their status.
    """
    params = dict(params or {})
    items: list = []
    while True:
        resp = call(client, method, path, params=params, **kwargs)
        if not 200 <= resp.status < 300:
            return resp
        items += resp.items()
        last_key = resp.body.get("lastKey") if isinstance(resp.body, dict) else None
        if resp.contains(token) or not last_key:
            return Response(resp.status, {"Items": items})
        params["startKey"] = last_key
