from enum import Enum

from pydantic import AliasChoices, Field

from albert.resources.base import BaseResource


class TagEntity(str, Enum):
    """TagEntity is an enumeration of possible tag entities."""

    INVENTORY = "Inventory"
    COMPANY = "Company"


class Tag(BaseResource):
    """
    Tag is a Pydantic model representing a tag entity.

    Attributes
    ----------
    tag : str
        The name of the tag.
    id : str | None
        The Albert ID of the tag. Set when the tag is retrieved from Albert.

    Methods
    -------
    from_string(tag: str) -> "Tag"
        Creates a Tag object from a string.
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
    def from_string(cls, tag: str) -> "Tag":
        """
        Creates a Tag object from a string.

        Parameters
        ----------
        tag : str
            The name of the tag.

        Returns
        -------
        Tag
            The Tag object created from the string.
        """
        return cls(tag=tag)
