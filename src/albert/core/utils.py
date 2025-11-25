"""Utility helpers shared across Albert SDK modules."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

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
