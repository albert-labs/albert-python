"""Delete CAS records that fail SDK parsing when encountered during integration tests."""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from albert.core.pagination import AlbertPaginator
from albert.exceptions import AlbertException, BadRequestError, ForbiddenError, NotFoundError
from albert.resources.cas import Cas
from albert.resources.custom_fields import ServiceType

if TYPE_CHECKING:
    from albert import Albert

_deleted_cas_ids: set[str] = set()
_installed = False


def deleted_cas_ids() -> frozenset[str]:
    """Return CAS IDs deleted after corrupted metadata was encountered."""
    return frozenset(_deleted_cas_ids)


def _delete_corrupted_cas(client: Albert, *, cas_id: str) -> None:
    if cas_id in _deleted_cas_ids:
        return
    _deleted_cas_ids.add(cas_id)
    with suppress(NotFoundError, BadRequestError, ForbiddenError):
        client.cas_numbers.delete(id=cas_id)


def _is_corrupted_cas_payload(item: dict[str, Any]) -> bool:
    metadata = item.get("Metadata") or {}
    if any("sup1894" in key for key in metadata):
        return True
    return any(_is_corrupted_list_metadata(value) for value in metadata.values())


def _is_corrupted_list_metadata(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.startswith("LST") for item in value)
    )


def delete_corrupted_cas_in_recent_pages(
    client: Albert,
    *,
    max_clean_pages: int = 5,
    max_pages: int = 50,
) -> list[str]:
    """Delete corrupted CAS records from recent pages without scanning the full catalog."""
    deleted: list[str] = []
    start_key: str | None = None
    clean_pages = 0
    pages_scanned = 0

    while clean_pages < max_clean_pages and pages_scanned < max_pages:
        params: dict[str, Any] = {"orderBy": "desc"}
        if start_key is not None:
            params["startKey"] = start_key
        response = client.session.get("/api/v3/cas", params=params)
        payload = response.json()
        items = payload.get("Items") or []
        pages_scanned += 1
        page_had_corruption = False

        for item in items:
            if not _is_corrupted_cas_payload(item):
                continue
            cas_id = item.get("albertId")
            if not isinstance(cas_id, str):
                continue
            page_had_corruption = True
            if cas_id not in _deleted_cas_ids:
                _delete_corrupted_cas(client, cas_id=cas_id)
                deleted.append(cas_id)

        clean_pages = 0 if page_had_corruption else clean_pages + 1
        start_key = payload.get("lastKey")
        if not items or not start_key:
            break

    return deleted


def deserialize_cas_items(client: Albert, items: Iterable[dict[str, Any]]) -> list[Cas]:
    """Parse CAS payloads, deleting and skipping records with corrupted list metadata."""
    parsed: list[Cas] = []
    for item in items:
        try:
            parsed.append(Cas(**item))
        except ValidationError:
            cas_id = item.get("albertId")
            if isinstance(cas_id, str):
                _delete_corrupted_cas(client, cas_id=cas_id)
    return parsed


def parse_cas_response(client: Albert, payload: dict[str, Any]) -> Cas:
    """Parse a single CAS payload, deleting the record when metadata is corrupted."""
    parsed = deserialize_cas_items(client, [payload])
    if not parsed:
        cas_id = payload.get("albertId")
        raise AlbertException(
            f"CAS {cas_id} was deleted after corrupted list metadata was encountered in tests."
        )
    return parsed[0]


def delete_sup1894_cas_custom_fields(client: Albert) -> list[str]:
    """Remove RCA custom fields that are safe to delete before tests run."""
    removed: list[str] = []
    for field in client.custom_fields.get_all(service=ServiceType.CAS, max_items=1000):
        if "sup1894" not in field.name:
            continue
        removed.append(field.name)
        with suppress(NotFoundError):
            client.custom_fields.delete(id=field.id)
    return removed


def install_cas_test_cleanup(client: Albert) -> None:
    """Patch CAS reads so corrupted records encountered in tests are deleted."""
    global _installed
    if _installed:
        return
    _installed = True

    import albert.collections.cas as cas_module

    removed_fields = delete_sup1894_cas_custom_fields(client)
    removed_cas = delete_corrupted_cas_in_recent_pages(client)
    if removed_fields or removed_cas:
        print(
            "\nCAS test cleanup at session start:"
            f" deleted {len(removed_cas)} corrupted CAS record(s)"
            f" and {len(removed_fields)} sup1894 custom field(s)."
        )

    original_paginator_init = AlbertPaginator.__init__

    def paginator_init(
        self,
        *,
        path: str,
        mode,
        session,
        deserialize,
        params: dict[str, str] | None = None,
        method: str = "GET",
        json: dict[str, Any] | None = None,
        max_items: int | None = None,
    ):
        if "/cas" in path:
            deserialize = lambda items: deserialize_cas_items(client, items)
        original_paginator_init(
            self,
            path=path,
            mode=mode,
            session=session,
            deserialize=deserialize,
            params=params,
            method=method,
            json=json,
            max_items=max_items,
        )

    AlbertPaginator.__init__ = paginator_init  # type: ignore[method-assign]

    def get_by_id(self, *, id: str) -> Cas:
        url = f"{self.base_path}/{id}"
        response = self.session.get(url)
        return parse_cas_response(client, response.json())

    cas_module.CasCollection.get_by_id = get_by_id  # type: ignore[method-assign]
