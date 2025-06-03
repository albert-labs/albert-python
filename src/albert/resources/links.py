from enum import Enum

from pydantic import Field

from albert.resources.base import BaseResource, EntityLink


class LinkCategory(str, Enum):
    MENTION = "mention"
    LINKED_TASK = "linkedTask"
    SYNTHESIS = "synthesis"
    LINKED_INVENTORY = "linkedInventory"


class Link(BaseResource):
    """A link in Albert.

    Attributes
    ----------
    parent : EntityLink
        The parent entity of the link.
    child : EntityLink
        The child entity of the link.
    category : LinkCategory
        The category of the link. Allowed values are `mention`, `linkedTask`, and `synthesis`.
    id : str | None
        The Albert ID of the link. Set when the link is retrieved from Albert.
    counter : int | None
        The counter of the link. Optional.

    """

    parent: EntityLink = Field(..., alias="Parent")
    child: EntityLink = Field(..., alias="Child")
    category: LinkCategory = Field(...)
    counter: int | None = Field(default=None)

    id: str | None = Field(default=None, alias="albertId")
