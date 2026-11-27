from enum import Enum
from typing import Any

from pydantic import AliasChoices, Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import BaseResource


class PersonalizationCategory(str, Enum):
    """The category of a personalization record.

    - ``STARRED_PROJECTS``: projects the user has starred (pinned).
    - ``HIDDEN_ROWS``: projects or inventory items the user has hidden.
    - ``SAVED_FILTERS``: saved filter views, grouped by ``sub_category``.
    - ``USER_CONFIGURATION``: the user's configuration (one record per user).
    - ``NOTIFICATION``: the user's notification preferences (one record per user).
    - ``SKILLS``: the user's disabled-skills list (one record per user).
    """

    STARRED_PROJECTS = "Starred Projects"
    HIDDEN_ROWS = "Hidden Rows"
    SAVED_FILTERS = "Saved Filters"
    USER_CONFIGURATION = "User Configuration"
    NOTIFICATION = "Notification"
    SKILLS = "Skills"


class PersonalizationFilter(BaseAlbertModel):
    """A saved filter entry on a personalization record."""

    filter_name: str | None = Field(default=None, alias="filterName")
    """The display name of the filter."""

    url: str | None = Field(default=None)
    """The URL the filter points to."""

    filter_type: str | None = Field(default=None, alias="filterType")
    """The type of the filter (e.g. ``Default`` or ``Custom``)."""


class Personalization(BaseResource):
    """A user personalization record in Albert.

    Personalization records store per-user preferences such as starred projects,
    hidden rows, and saved filters. They are managed through the
    [`PersonalizationCollection`][albert.collections.personalization.PersonalizationCollection].

    !!! example
        ```python
        from albert.resources.personalization import Personalization, PersonalizationCategory

        record = Personalization(
            category=PersonalizationCategory.STARRED_PROJECTS,
            saved_id="PRO123",
            saved_name="Weatherproof Coatings 2026",
        )
        ```
    """

    id: str | None = Field(
        default=None, alias="albertId", validation_alias=AliasChoices("albertId", "id")
    )
    """The Albert ID of the record (format ``USP...``). Assigned by Albert when the record is created."""

    category: PersonalizationCategory
    """The category of the record."""

    sub_category: str | None = Field(default=None, alias="subCategory")
    """The subcategory of the record (e.g. the entity a saved filter applies to)."""

    parent_id: str | None = Field(default=None, alias="parentId")
    """The ID of the user the record belongs to. Assigned from the authenticated session when the record is created."""

    saved_id: str | None = Field(default=None, alias="savedId")
    """The ID of the saved entity (e.g. a Project ID for a starred project)."""

    saved_name: str | None = Field(default=None, alias="savedName")
    """The display name of the saved entity."""

    metadata: dict[str, Any] | None = Field(default=None, alias="Metadata")
    """Arbitrary metadata key-value pairs stored on the record."""

    filters: list[PersonalizationFilter] | None = Field(default=None)
    """Saved filter entries, present on records in the Saved Filters category."""
