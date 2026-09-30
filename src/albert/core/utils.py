"""Utility helpers shared across Albert SDK modules."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, TypeVar

from albert.exceptions import AlbertPartialError

if TYPE_CHECKING:
    import requests

T = TypeVar("T")


def ensure_list(value: T | Iterable[T] | None) -> list[T] | None:
    """Return ``value`` as a list, preserving ``None`` and existing lists."""

    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, tuple | set):
        return list(value)
    return [value]


def unpack_bulk_created_items(response: requests.Response) -> list[dict[str, Any]]:
    """Unpack the created items from a bulk-operation response.

    Bulk endpoints report a partial success with HTTP 206 and a body shaped
    ``{"CreatedItems": [...], "FailedItems": [...]}`` instead of the usual bare list of
    created items. Any reported failure raises
    [`AlbertPartialError`][albert.exceptions.AlbertPartialError] so a partial success is
    never mistaken for a full one (or crashes item-wise parsing of the response).

    Parameters
    ----------
    response : requests.Response
        The response of a bulk create/merge request.

    Returns
    -------
    list[dict[str, Any]]
        The created items.

    Raises
    ------
    AlbertPartialError
        If the response reports any failed items.
    """
    data = response.json()
    if isinstance(data, list):
        return data
    created_items = data.get("CreatedItems") or []
    failed_items = data.get("FailedItems") or []
    if failed_items:
        raise AlbertPartialError(
            f"Bulk operation partially succeeded: {len(created_items)} item(s) created, "
            f"{len(failed_items)} item(s) failed. Failures: {failed_items}",
            created_items=created_items,
            failed_items=failed_items,
        )
    return created_items
