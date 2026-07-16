from __future__ import annotations

from enum import Enum

from pydantic import AliasChoices, Field

from albert.core.shared.models.base import BaseResource


class TagEntity(str, Enum):
    """The kind of entity a tag can be attached to.

    Attributes
    ----------
    INVENTORY : str
        Inventory items.
    COMPANY : str
        Companies.
    """

    INVENTORY = "Inventory"
    COMPANY = "Company"


class Tag(BaseResource):
    """A freeform text label used to categorize and connect entities.

    Tags are shared by name across the platform and can be applied to inventory
    items, companies, tasks, and other records to group and filter them. Managed
    through [`TagCollection`][albert.collections.tags.TagCollection] (``client.tags``);
    the usual entry point is [`get_or_create`][albert.collections.tags.TagCollection.get_or_create].

    Attributes
    ----------
    tag : str
        The name of the tag (its text label).
    id : str or None
        The Albert ID of the tag (format ``TAG...``). Set when the tag is
        retrieved from or created in Albert.

    Methods
    -------
    from_string(tag) -> Tag
        Build a Tag from its name string.

    !!! example
        ```python
        from albert.resources.tags import Tag
        tag = Tag(tag="high-priority")
        ```
    """

    # different endpoints use different aliases for the fields
    # the search endpoints use the 'tag' prefix in their results.
    tag: str = Field(
        alias=AliasChoices("name", "tagName"),
        serialization_alias="name",
    )
    id: str | None = Field(
        None,
        alias=AliasChoices("albertId", "tagId"),
        serialization_alias="albertId",
    )

    @classmethod
    def from_string(cls, tag: str) -> Tag:
        """Build a Tag from its name string.

        Parameters
        ----------
        tag : str
            The name of the tag.

        Returns
        -------
        Tag
            A Tag with the given name.

        !!! example
            ```python
            from albert.resources.tags import Tag
            tag = Tag.from_string("experimental")
            ```
        """
        return cls(tag=tag)
