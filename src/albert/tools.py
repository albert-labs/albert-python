"""
Albert Tool Decorator — marks SDK collection methods for auto-discovery as MCP tools.

SDK developers add @albert_tool to any collection method they want surfaced
as an agent tool. The MCP server scans for these at boot and registers them
automatically via FastMCP — no manual wiring required.

Example usage in a collection:

    from albert.tools import albert_tool

    class ProjectCollection(BaseCollection):

        @albert_tool(category="projects")
        def search(self, *, text: str | None = None, max_items: int | None = None):
            \"""
            Search for projects by name or keyword.

            Args:
                text: Full-text search query — project name or keyword.
                max_items: Maximum number of results to return.
            \"""
            ...

        @albert_tool(category="projects", write=True, confirm=True)
        def create(self, *, project: Project) -> Project:
            \"""Create a new project in Albert.\"""
            ...

The decorator is pure Python with no external dependencies.
It attaches metadata to the method via _albert_tool_meta attribute.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class AlbertToolMeta:
    """Metadata attached to a method by @albert_tool."""

    category: str
    """Logical resource group: 'projects', 'inventory', etc."""

    write: bool = False
    """True if this method creates, updates, or deletes data."""

    confirm: bool = False
    """True if the agent must ask the user to confirm before executing."""

    name: str | None = None
    """Override the auto-generated tool name. Default: {verb}_{category}."""

    tags: tuple[str, ...] = field(default_factory=tuple)
    """Extra keywords to assist skill routing."""


_SENTINEL = object()


def albert_tool(
    category: str,
    *,
    write: bool = False,
    confirm: bool = False,
    name: str | None = None,
    tags: list[str] | None = None,
) -> Callable:
    """
    Decorator that marks a collection method for auto-discovery as an MCP tool.

    Parameters
    ----------
    category : str
        Logical resource group (e.g. ``"projects"``, ``"inventory"``).
        Used to generate the tool name and for skill routing.
    write : bool, optional
        Set ``True`` for methods that create, update, or delete data.
        The MCP server will enforce a write-safety gate for these tools.
    confirm : bool, optional
        Set ``True`` if the agent must summarise the action and get
        explicit user confirmation before calling the method.
    name : str, optional
        Override the auto-generated tool name.
        Default pattern: ``{verb}_{category}`` (e.g. ``search_projects``).
    tags : list[str], optional
        Extra keywords for semantic skill retrieval routing.
    """
    meta = AlbertToolMeta(
        category=category,
        write=write,
        confirm=confirm,
        name=name,
        tags=tuple(tags or []),
    )

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        wrapper._albert_tool_meta = meta  # type: ignore[attr-defined]
        return wrapper

    return decorator


def get_tool_meta(fn: Callable) -> AlbertToolMeta | None:
    """Return AlbertToolMeta if the function was decorated with @albert_tool, else None."""
    return getattr(fn, "_albert_tool_meta", None)


def is_albert_tool(fn: object) -> bool:
    """Return True if the callable has been decorated with @albert_tool."""
    return hasattr(fn, "_albert_tool_meta")
