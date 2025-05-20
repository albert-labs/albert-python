from enum import Enum

from pydantic import Field, model_validator

from albert.resources.base import BaseResource


class ListItemCategory(str, Enum):
    BUSINESS_DEFINED = "businessDefined"
    USER_DEFINED = "userDefined"
    PROJECTS = "projects"
    EXTENSIONS = "extensions"
    INVENTORY = "inventory"


class ListItem(BaseResource):
    """An item in a list.

    Attributes
    ----------
    name : str
        The name of the list item.
    id : str | None
        The Albert ID of the list item. Set when the list item is retrieved from Albert.
    category : ListItemCategory | None
        The category of the list item. Allowed values are `businessDefined`, `userDefined`, `projects`, and `extensions`.
    list_type : str | None
        The type of the list item. Allowed values are `projectState` for `projects` and `extensions` for `extensions`.
    """

    name: str
    id: str | None = Field(default=None, alias="albertId")
    category: ListItemCategory | None = Field(default=None)
    list_type: str | None = Field(default=None, alias="listType")

    @model_validator(mode="after")
    def validate_list_type(self) -> "ListItem":
        if (
            self.category == ListItemCategory.PROJECTS
            and self.list_type is not None
            and self.list_type != "projectState"
        ) or (
            self.category == ListItemCategory.EXTENSIONS
            and self.list_type is not None
            and self.list_type != "extensions"
        ):
            raise ValueError(
                f"List type {self.list_type} is not allowed for category {self.category}"
            )
        return self
