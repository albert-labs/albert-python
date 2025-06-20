import logging
from typing import Any

from pydantic import Field, model_validator

from albert.resources.base import BaseResource
from albert.resources.serialization import SerializeAsEntityLink
from albert.resources.tags import Tag


class BaseTaggedResource(BaseResource):
    """
    BaseTaggedResource is a Pydantic model that includes functionality for handling tags as either Tag objects or strings.

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
                    logging.warning(f"Unexpected value for Tag. {t} of type {type(t)}")
                    continue
            data["tags"] = new_tags
        return data
