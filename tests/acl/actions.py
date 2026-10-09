"""Read-path probes: each way of reading a record is its own action.

Paths come from the service REST definitions (identification only). Each probe returns
``(method, path, kwargs)`` given the record id and its canary token.
"""

from collections.abc import Callable

from tests.acl.contract.fgc import Kind, ReadPath

P = ReadPath
ProbeFn = Callable[[str, str], tuple[str, str, dict]]

READ_PATHS: dict[Kind, dict[ReadPath, ProbeFn]] = {
    Kind.PROJECT: {
        P.GET_BY_ID: lambda i, c: ("GET", f"/api/v3/projects/{i}", {}),
        P.LIST: lambda i, c: ("GET", "/api/v3/projects", {"params": {"limit": 100}}),
        P.SEARCH_GET: lambda i, c: ("GET", "/api/v3/projects/search", {"params": {"text": c}}),
        P.SEARCH_POST: lambda i, c: (
            "POST",
            "/api/v3/projects/search",
            {"json": {"text": c, "limit": 50, "offset": 0}},
        ),
        P.SUGGEST: lambda i, c: ("GET", "/api/v3/projects/suggest", {"params": {"text": c}}),
        P.DOCUMENT_SEARCH: lambda i, c: (
            "GET",
            "/api/v3/projects/documentsearch",
            {"params": {"text": c}},
        ),
    },
    Kind.GENERAL_TASK: {
        P.GET_BY_ID: lambda i, c: ("GET", f"/api/v3/tasks/{i}", {}),
        P.LIST: lambda i, c: ("GET", "/api/v3/tasks", {"params": {"limit": 100}}),
        P.SEARCH_GET: lambda i, c: ("GET", "/api/v3/tasks/search", {"params": {"text": c}}),
        P.SEARCH_POST: lambda i, c: (
            "POST",
            "/api/v3/tasks/search",
            {"json": {"text": c, "limit": 50, "offset": 0}},
        ),
        P.SUGGEST: lambda i, c: ("GET", "/api/v3/tasks/suggest", {"params": {"text": c}}),
    },
    Kind.INVENTORY: {
        P.GET_BY_ID: lambda i, c: ("GET", f"/api/v3/inventories/{i}", {}),
        P.BULK_IDS: lambda i, c: ("GET", "/api/v3/inventories/ids", {"params": {"id": [i]}}),
        P.LIST: lambda i, c: (
            "GET",
            "/api/v3/inventories",
            {"params": {"name": c, "exactMatch": "false"}},
        ),
        P.SEARCH_GET: lambda i, c: (
            "GET",
            "/api/v3/inventories/search",
            {"params": {"text": c}},
        ),
        P.SEARCH_POST: lambda i, c: (
            "POST",
            "/api/v3/inventories/search",
            {"json": {"text": c, "limit": 50, "offset": 0}},
        ),
        P.SUGGEST: lambda i, c: ("GET", "/api/v3/inventories/suggest", {"params": {"text": c}}),
        P.LLMSEARCH: lambda i, c: (
            "GET",
            "/api/v3/inventories/llmsearch",
            {"params": {"text": c}},
        ),
    },
    Kind.LOT: {
        P.GET_BY_ID: lambda i, c: ("GET", f"/api/v3/lots/{i}", {}),
        P.BULK_IDS: lambda i, c: ("GET", "/api/v3/lots/ids", {"params": {"id": [i]}}),
    },
    Kind.PROJECT_CHILD: {
        P.GET_BY_ID: lambda i, c: ("GET", f"/api/v3/notebooks/{i}", {}),
        P.SEARCH_GET: lambda i, c: (
            "GET",
            "/api/v3/notebooks/search",
            {"params": {"text": c, "globalSearch": "true"}},
        ),
    },
    Kind.TASK_CHILD: {
        P.GET_BY_ID: lambda i, c: ("GET", f"/api/v3/notes/{i}", {}),
    },
    Kind.INVENTORY_CHILD: {
        P.GET_BY_ID: lambda i, c: ("GET", f"/api/v3/notes/{i}", {}),
    },
}

DIRECT = frozenset({P.GET_BY_ID, P.BULK_IDS})
