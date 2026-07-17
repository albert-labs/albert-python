from enum import Enum

from pydantic import Field

from albert.core.shared.models.base import BaseResource, EntityLink


class LinkCategory(str, Enum):
    """The kind of relationship a link represents."""

    MENTION = "mention"
    """One entity mentions another (e.g. a user or entity referenced in a note)."""
    LINKED_TASK = "linkedTask"
    """A task linked to another entity."""
    SYNTHESIS = "synthesis"
    """A synthesis relationship between entities."""
    LINKED_INVENTORY = "linkedInventory"
    """An inventory item linked to another entity."""


class Link(BaseResource):
    """A directional relationship between two entities in Albert.

    A link connects a ``parent`` entity to a ``child`` entity under a given
    [`LinkCategory`][albert.resources.links.LinkCategory]. Links are managed through the
    [`LinksCollection`][albert.collections.links.LinksCollection].

    !!! example
        ```python
        from albert.resources.links import Link, LinkCategory
        from albert.core.shared.models.base import EntityLink
        link = Link(
            parent=EntityLink(id="INVA1"),
            child=EntityLink(id="INVA2"),
            category=LinkCategory.LINKED_INVENTORY,
        )
        ```"""

    parent: EntityLink = Field(..., alias="Parent")
    """The parent (source) entity of the link."""
    child: EntityLink = Field(..., alias="Child")
    """The child (target) entity of the link."""
    category: LinkCategory = Field(...)
    """The category of the link (e.g. ``mention``, ``linkedTask``, ``synthesis``, ``linkedInventory``)."""
    counter: int | None = Field(default=None)
    """An optional counter associated with the link."""

    id: str | None = Field(default=None, alias="albertId")
    """The Albert ID of the link (format ``LNK...``). Assigned by Albert when the link is created."""
