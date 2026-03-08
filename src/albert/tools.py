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
            \"""
            Create a new project in Albert.

            Args:
                project: The Project object to create. Must include name and location.
            \"""
            ...

Docstring parsing uses griffe (already a transitive dependency via griffe-pydantic).
Supports Google-style (Args:) and NumPy-style (Parameters\\n---) out of the box.

Validation rules (enforced by validate_albert_tool, called by the scanner):
  - Decorated methods MUST have a docstring
  - All required parameters (no default) MUST have a description in the Args section
  - Optional parameters (have a default) SHOULD have descriptions — warning only
  - Unannotated return type — warning only
"""

from __future__ import annotations

import functools
import inspect
import logging
import warnings
from dataclasses import dataclass, field
from typing import Callable

import griffe

_griffe_logger = logging.getLogger("griffe")


# ── Metadata ──────────────────────────────────────────────────────────────────

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


# ── Exception ─────────────────────────────────────────────────────────────────

class AlbertToolValidationError(Exception):
    """
    Raised when a method decorated with @albert_tool fails validation.

    The scanner catches this and logs a warning rather than crashing,
    so a single bad method never prevents the MCP server from starting.
    """


# ── Decorator ─────────────────────────────────────────────────────────────────

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
    confirm : bool, optional
        Set ``True`` if the agent must confirm with the user before executing.
    name : str, optional
        Override the auto-generated tool name.
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


# ── Introspection ─────────────────────────────────────────────────────────────

def get_tool_meta(fn: Callable) -> AlbertToolMeta | None:
    """Return AlbertToolMeta if decorated with @albert_tool, else None."""
    return getattr(fn, "_albert_tool_meta", None)


def is_albert_tool(fn: object) -> bool:
    """Return True if the callable has been decorated with @albert_tool."""
    return hasattr(fn, "_albert_tool_meta")


# ── Docstring parsing (via griffe) ────────────────────────────────────────────

def parse_param_descriptions(fn: Callable) -> dict[str, str]:
    """
    Parse parameter descriptions from a method docstring using griffe.

    Supports Google-style (``Args:``) and NumPy-style (``Parameters\\n---``)
    docstrings. Auto-detects style.

    Parameters
    ----------
    fn : Callable
        The function whose docstring to parse.

    Returns
    -------
    dict[str, str]
        Mapping of parameter name to description. Empty dict if no Args section.
    """
    raw = inspect.getdoc(fn)
    if not raw:
        return {}

    doc = griffe.Docstring(raw)

    # Suppress griffe's "no type annotation" warnings — type hints come from
    # Python signatures, not docstrings.
    prev_level = _griffe_logger.level
    _griffe_logger.setLevel(logging.ERROR)
    try:
        sections = griffe.parse_auto(doc)
    finally:
        _griffe_logger.setLevel(prev_level)

    descriptions: dict[str, str] = {}
    for section in sections:
        if section.kind in (
            griffe.DocstringSectionKind.parameters,
            griffe.DocstringSectionKind.other_parameters,
        ):
            for param in section.value:
                if param.description:
                    descriptions[param.name] = param.description

    return descriptions


# ── Validation ────────────────────────────────────────────────────────────────

def validate_albert_tool(fn: Callable) -> None:
    """
    Validate that a method decorated with @albert_tool meets the requirements
    for safe MCP tool registration.

    Raises
    ------
    AlbertToolValidationError
        - Not decorated with @albert_tool
        - Missing or empty docstring
        - Required parameter (no default) has no description in Args section

    Warns
    -----
    UserWarning
        - Optional parameter has no description
        - Return type is unannotated (``-> None`` is valid, no warning)
    """
    if not is_albert_tool(fn):
        raise AlbertToolValidationError(
            f"{fn.__name__}: not decorated with @albert_tool"
        )

    doc = inspect.getdoc(fn)
    if not doc or not doc.strip():
        raise AlbertToolValidationError(
            f"{fn.__name__}: missing docstring. "
            "All @albert_tool methods must have a docstring — "
            "it is used as the tool description for the AI agent."
        )

    sig = inspect.signature(fn)
    param_descs = parse_param_descriptions(fn)

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        has_default = param.default is not inspect.Parameter.empty
        has_description = bool(param_descs.get(param_name, "").strip())

        if not has_default and not has_description:
            raise AlbertToolValidationError(
                f"{fn.__name__}: required parameter '{param_name}' has no description "
                f"in the docstring Args section. Required parameters must be documented "
                f"so the AI agent knows what to pass. Add an Args section:\n\n"
                f"    Args:\n"
                f"        {param_name}: <description of what this parameter is>\n"
            )

        if has_default and not has_description:
            warnings.warn(
                f"{fn.__name__}: optional parameter '{param_name}' has no description. "
                f"Adding a description helps the AI agent use this parameter correctly.",
                UserWarning,
                stacklevel=2,
            )

    if sig.return_annotation is inspect.Parameter.empty:
        warnings.warn(
            f"{fn.__name__}: return type is unannotated. "
            f"Add a return type annotation (e.g. -> list[Project] or -> None).",
            UserWarning,
            stacklevel=2,
        )
