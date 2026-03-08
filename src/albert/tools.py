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

Validation rules (enforced by validate_albert_tool, called by the scanner):
  - Decorated methods MUST have a docstring
  - All required parameters (no default) MUST have a description in the Args section
  - Optional parameters (have a default) SHOULD have descriptions — warning only
  - Unannotated return type — warning only
"""

from __future__ import annotations

import functools
import inspect
import re
import warnings
from dataclasses import dataclass, field
from typing import Callable


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


# ── Introspection helpers ─────────────────────────────────────────────────────

def get_tool_meta(fn: Callable) -> AlbertToolMeta | None:
    """Return AlbertToolMeta if the function was decorated with @albert_tool, else None."""
    return getattr(fn, "_albert_tool_meta", None)


def is_albert_tool(fn: object) -> bool:
    """Return True if the callable has been decorated with @albert_tool."""
    return hasattr(fn, "_albert_tool_meta")


# ── Docstring parsing ─────────────────────────────────────────────────────────

def parse_param_descriptions(fn: Callable) -> dict[str, str]:
    """
    Parse parameter descriptions from a method docstring.

    Supports Google-style (``Args:``) and NumPy-style (``Parameters``/``Parameters:``) sections.

    Returns a dict of {param_name: description_string}.
    Empty dict if no Args section is found.

    Examples
    --------
    Google style::

        Args:
            text: Full-text search query.
            max_items: Maximum number of results.

    NumPy style::

        Parameters
        ----------
        text : str
            Full-text search query.
    """
    doc = inspect.getdoc(fn) or ""
    descriptions: dict[str, str] = {}

    if not doc:
        return descriptions

    # Detect style
    if re.search(r"^Parameters\s*\n\s*-{3,}", doc, re.MULTILINE):
        descriptions = _parse_numpy_args(doc)
    else:
        descriptions = _parse_google_args(doc)

    return descriptions


def _parse_google_args(doc: str) -> dict[str, str]:
    """Parse Google-style Args section."""
    descriptions: dict[str, str] = {}
    in_args = False
    current_param: str | None = None
    current_lines: list[str] = []

    section_headers = {
        "Returns:", "Return:", "Yields:", "Raises:", "Note:", "Notes:",
        "Example:", "Examples:", "See Also:", "References:",
        "Attributes:", "Todo:",
    }

    for line in doc.splitlines():
        stripped = line.strip()

        if stripped in ("Args:", "Arguments:"):
            in_args = True
            continue

        if in_args:
            # Detect new top-level section (not indented)
            if stripped in section_headers or (stripped.endswith(":") and not line.startswith(" ")):
                break

            # Detect a new parameter: 4-8 spaces indent + word + colon or type hint
            m = re.match(r"^( {4,8})(\w+)\s*[:(]", line)
            if m:
                if current_param:
                    descriptions[current_param] = " ".join(current_lines).strip()
                current_param = m.group(2)
                current_lines = []
                # Capture inline description after "name:" or "name (type):"
                rest = re.sub(r"^\s*\w+\s*(?:\([^)]*\))?\s*:\s*", "", line).strip()
                if rest:
                    current_lines.append(rest)
            elif current_param and stripped:
                # Continuation line for current param
                current_lines.append(stripped)

    if current_param and current_lines:
        descriptions[current_param] = " ".join(current_lines).strip()

    return descriptions


def _parse_numpy_args(doc: str) -> dict[str, str]:
    """Parse NumPy-style Parameters section."""
    descriptions: dict[str, str] = {}
    lines = doc.splitlines()
    in_params = False
    in_divider = False
    current_param: str | None = None
    current_lines: list[str] = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        if re.match(r"^Parameters\s*$", stripped):
            in_params = True
            continue

        if in_params and re.match(r"^-{3,}$", stripped):
            in_divider = True
            continue

        if in_params and in_divider:
            # New top-level section
            if re.match(r"^\w.*\n?\s*-{3,}", "\n".join(lines[i:i+2])):
                break
            # New param: "name" or "name : type"
            m = re.match(r"^(\w+)\s*(?::\s*.+)?$", stripped)
            if m and line and not line.startswith(" "):
                if current_param and current_lines:
                    descriptions[current_param] = " ".join(current_lines).strip()
                current_param = m.group(1)
                current_lines = []
            elif current_param and stripped:
                current_lines.append(stripped)

    if current_param and current_lines:
        descriptions[current_param] = " ".join(current_lines).strip()

    return descriptions


# ── Validation ────────────────────────────────────────────────────────────────

def validate_albert_tool(fn: Callable) -> None:
    """
    Validate that a method decorated with @albert_tool meets the requirements
    for safe MCP tool registration.

    Raises
    ------
    AlbertToolValidationError
        If the method is not decorated with @albert_tool, has no docstring,
        or has required parameters without descriptions.

    Warns
    -----
    UserWarning
        If optional parameters lack descriptions or the return type is unannotated.

    Notes
    -----
    Validation rules:
    - Must be decorated with @albert_tool
    - Must have a non-empty docstring (Claude reads this as the tool description)
    - All required params (no default, not 'self') must have a description in Args
    - Optional params without descriptions emit a warning
    - Unannotated return type emits a warning
    - ``-> None`` is an explicit valid annotation — no warning
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
        has_description = param_name in param_descs and bool(param_descs[param_name].strip())

        if not has_default and not has_description:
            raise AlbertToolValidationError(
                f"{fn.__name__}: required parameter '{param_name}' has no description in the "
                f"docstring Args section. Required parameters must be documented so the AI agent "
                f"knows what to pass. Add an Args section:\n\n"
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

    # Check return annotation
    return_ann = sig.return_annotation
    if return_ann is inspect.Parameter.empty:
        warnings.warn(
            f"{fn.__name__}: return type is unannotated. "
            f"Add a return type annotation (e.g. -> list[Project] or -> None) "
            f"so the agent knows what to expect back.",
            UserWarning,
            stacklevel=2,
        )
