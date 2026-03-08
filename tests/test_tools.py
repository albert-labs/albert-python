"""
Unit tests for albert/tools.py — decorator, docstring parsing, and validation.

These are pure unit tests with no network calls or Albert client required.

Validation rules:
  - Decorated methods MUST have a docstring (Claude reads it as the tool description)
  - All required parameters (no default) MUST have a description in the Args section
  - Optional parameters (have a default) SHOULD have descriptions — warning only
  - Unannotated return type — warning only (doesn't break anything)
  - Malformed / missing Args section — warning for optional params, error for required ones
"""
from __future__ import annotations

import inspect
import pytest

from albert.tools import (
    AlbertToolMeta,
    AlbertToolValidationError,
    albert_tool,
    get_tool_meta,
    is_albert_tool,
    validate_albert_tool,
)


# ── Fixtures / helpers ────────────────────────────────────────────────────────

def make_method(fn):
    """Wrap a plain function to look like an unbound method for testing."""
    return fn


# ── Decorator basics ──────────────────────────────────────────────────────────

class TestDecorator:
    def test_attaches_meta(self):
        @albert_tool(category="projects")
        def search(self, text: str | None = None) -> list:
            """Search projects.

            Args:
                text: Full-text search query.
            """

        assert is_albert_tool(search)
        meta = get_tool_meta(search)
        assert isinstance(meta, AlbertToolMeta)
        assert meta.category == "projects"
        assert meta.write is False
        assert meta.confirm is False

    def test_write_flag(self):
        @albert_tool(category="projects", write=True, confirm=True)
        def create(self, name: str) -> dict:
            """Create a project.

            Args:
                name: Project name.
            """

        meta = get_tool_meta(create)
        assert meta.write is True
        assert meta.confirm is True

    def test_name_override(self):
        @albert_tool(category="projects", name="find_projects")
        def search(self, text: str | None = None) -> list:
            """Search projects.

            Args:
                text: Full-text search query.
            """

        meta = get_tool_meta(search)
        assert meta.name == "find_projects"

    def test_tags(self):
        @albert_tool(category="inventory", tags=["stock", "materials"])
        def search(self, text: str | None = None) -> list:
            """Search inventory.

            Args:
                text: Search query.
            """

        meta = get_tool_meta(search)
        assert "stock" in meta.tags
        assert "materials" in meta.tags

    def test_preserves_function_name(self):
        @albert_tool(category="projects")
        def search(self, text: str | None = None) -> list:
            """Search projects.

            Args:
                text: Full-text search query.
            """

        assert search.__name__ == "search"

    def test_preserves_docstring(self):
        @albert_tool(category="projects")
        def search(self, text: str | None = None) -> list:
            """Search projects by name.

            Args:
                text: Full-text search query.
            """

        assert "Search projects by name" in inspect.getdoc(search)

    def test_preserves_behaviour(self):
        @albert_tool(category="projects")
        def add(self, a: int, b: int) -> int:
            """Add two numbers.

            Args:
                a: First number.
                b: Second number.
            """
            return a + b

        assert add(None, 1, 2) == 3

    def test_not_decorated(self):
        def plain(self, text: str) -> list:
            """Plain function."""

        assert not is_albert_tool(plain)
        assert get_tool_meta(plain) is None


# ── Docstring parsing ─────────────────────────────────────────────────────────

class TestDocstringParsing:
    """Tests for the Args section parser used by the scanner."""

    def test_google_style_args(self):
        @albert_tool(category="projects")
        def search(self, text: str, max_items: int = 10) -> list:
            """Search projects.

            Args:
                text: Full-text search query — project name or keyword.
                max_items: Maximum number of results to return.
            """

        from albert.tools import parse_param_descriptions
        descs = parse_param_descriptions(search)
        assert descs["text"] == "Full-text search query — project name or keyword."
        assert descs["max_items"] == "Maximum number of results to return."

    def test_numpy_style_args(self):
        @albert_tool(category="projects")
        def get_by_id(self, id: str) -> dict:
            """Get project by ID.

            Parameters
            ----------
            id : str
                The Albert project ID to retrieve.
            """

        from albert.tools import parse_param_descriptions
        descs = parse_param_descriptions(get_by_id)
        assert "id" in descs
        assert "Albert project ID" in descs["id"]

    def test_multiline_param_description(self):
        @albert_tool(category="inventory")
        def search(self, text: str, category: str | None = None) -> list:
            """Search inventory.

            Args:
                text: Full-text search query for inventory items
                    including raw materials and chemicals.
                category: Filter by inventory category.
            """

        from albert.tools import parse_param_descriptions
        descs = parse_param_descriptions(search)
        assert "raw materials" in descs["text"]

    def test_no_args_section(self):
        @albert_tool(category="projects")
        def list_all(self, max_items: int = 10) -> list:
            """List all projects."""

        from albert.tools import parse_param_descriptions
        descs = parse_param_descriptions(list_all)
        assert descs == {}

    def test_empty_docstring_returns_empty(self):
        @albert_tool(category="projects")
        def search(self, text: str) -> list:
            """"""

        from albert.tools import parse_param_descriptions
        descs = parse_param_descriptions(search)
        assert descs == {}

    def test_args_section_stops_at_next_section(self):
        @albert_tool(category="projects")
        def search(self, text: str) -> list:
            """Search projects.

            Args:
                text: Search query.

            Returns:
                List of matching projects.
            """

        from albert.tools import parse_param_descriptions
        descs = parse_param_descriptions(search)
        assert "text" in descs
        assert "Returns" not in descs


# ── Validation ────────────────────────────────────────────────────────────────

class TestValidation:
    """Tests for validate_albert_tool() — called by the scanner before registering."""

    def test_valid_method_passes(self):
        @albert_tool(category="projects")
        def search(self, text: str, max_items: int = 10) -> list:
            """Search projects by name or keyword.

            Args:
                text: Full-text search query.
                max_items: Maximum number of results.
            """

        # Should not raise
        validate_albert_tool(search)

    def test_missing_docstring_raises(self):
        @albert_tool(category="projects")
        def search(self, text: str) -> list:
            pass

        with pytest.raises(AlbertToolValidationError, match="missing docstring"):
            validate_albert_tool(search)

    def test_required_param_missing_description_raises(self):
        """Required params (no default) must have descriptions — Claude needs them."""
        @albert_tool(category="projects")
        def get_by_id(self, id: str) -> dict:
            """Get a project by ID."""
            # 'id' is required but has no Args section description

        with pytest.raises(AlbertToolValidationError, match="required.*'id'"):
            validate_albert_tool(get_by_id)

    def test_optional_param_missing_description_warns(self, recwarn):
        """Optional params missing descriptions get a warning, not an error."""
        @albert_tool(category="projects")
        def search(self, text: str, max_items: int = 10) -> list:
            """Search projects.

            Args:
                text: Full-text search query.
            """
            # max_items has a default but no description

        validate_albert_tool(search)  # should not raise
        assert any("max_items" in str(w.message) for w in recwarn.list)

    def test_multiple_required_params_all_need_descriptions(self):
        @albert_tool(category="projects")
        def create(self, name: str, location_id: str) -> dict:
            """Create a new project.

            Args:
                name: Project name.
            """
            # location_id is required but undescribed

        with pytest.raises(AlbertToolValidationError, match="required.*'location_id'"):
            validate_albert_tool(create)

    def test_unannotated_return_warns(self, recwarn):
        """Unannotated return type is a warning — scanner can proceed."""
        @albert_tool(category="projects")
        def search(self, text: str):
            """Search projects.

            Args:
                text: Search query.
            """

        validate_albert_tool(search)  # should not raise
        assert any("return" in str(w.message).lower() for w in recwarn.list)

    def test_none_return_is_valid(self):
        """-> None is an explicit annotation and should pass without warning."""
        @albert_tool(category="projects", write=True, confirm=True)
        def delete(self, id: str) -> None:
            """Delete a project by ID.

            Args:
                id: The Albert project ID to delete.
            """

        validate_albert_tool(delete)  # should not raise or warn

    def test_self_param_excluded_from_validation(self):
        """'self' should never require a description."""
        @albert_tool(category="projects")
        def search(self, text: str) -> list:
            """Search projects.

            Args:
                text: Full-text search query.
            """

        validate_albert_tool(search)  # should not raise about 'self'

    def test_only_optional_params_no_args_section_warns_not_raises(self, recwarn):
        """A method with only optional params and no Args section gets warnings, not errors."""
        @albert_tool(category="projects")
        def list_all(self, max_items: int = 20, offset: int = 0) -> list:
            """List all projects."""

        validate_albert_tool(list_all)  # should not raise

    def test_not_decorated_raises(self):
        def plain(self, text: str) -> list:
            """Plain function."""

        with pytest.raises(AlbertToolValidationError, match="not decorated"):
            validate_albert_tool(plain)
