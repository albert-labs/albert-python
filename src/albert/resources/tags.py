from enum import Enum
from typing import Any

from pydantic import AliasChoices, Field, model_validator

from albert.core.logging import logger
from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import SerializeAsEntityLink


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


class BaseTaggedEntity(BaseResource):
    """
    BaseTaggedEntity is a Pydantic model that includes functionality for handling tags as either Tag objects or strings.

    Attributes
    ----------
    tags : List[Tag | str] | None
        A list of Tag objects or strings representing tags.
    """

    tags: list[SerializeAsEntityLink[Tag]] | None = Field(None, alias="Tags")

    @model_validator(mode="before")  # must happen before to keep type validation
    @classmethod
    def convert_tags(cls, data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            return data
        tags = data.get("tags")
        if not tags:
            tags = data.get("Tags")
        if tags:
            new_tags = []
            for t in tags:
                if isinstance(t, Tag):
                    new_tags.append(t)
                elif isinstance(t, str):
                    new_tags.append(Tag.from_string(t))
                elif isinstance(t, dict):
                    new_tags.append(Tag(**t))
                else:
                    # We do not expect this else to be hit because tags should only be Tag or str
                    logger.warning(f"Unexpected value for Tag. {t} of type {type(t)}")
                    continue
            data["tags"] = new_tags
        return data
