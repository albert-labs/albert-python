from enum import Enum

from pydantic import Field

from albert.resources.base import BaseResource, EntityLinkConvertible


class TagEntity(str, Enum):
    """TagEntity is an enumeration of possible tag entities."""

    INVENTORY = "Inventory"
    COMPANY = "Company"


class Tag(BaseResource, EntityLinkConvertible):
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

    tag: str = Field(alias="name")
    id: str | None = Field(None, alias="albertId")

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
