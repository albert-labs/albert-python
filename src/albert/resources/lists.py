from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from albert.core.shared.models.base import BaseResource


class ListItemCategory(str, Enum):
    """The category a list item belongs to, which governs its allowed list types.

    Attributes
    ----------
    BUSINESS_DEFINED : str
        Predefined values managed at the business/organization level.
    USER_DEFINED : str
        Custom values defined by users.
    PROJECTS : str
        Values used by projects (e.g. project states).
    EXTENSIONS : str
        Values used by extensions.
    INVENTORY : str
        Values used by inventory (e.g. CAS categories or inventory functions).
    """

    BUSINESS_DEFINED = "businessDefined"
    USER_DEFINED = "userDefined"
    PROJECTS = "projects"
    EXTENSIONS = "extensions"
    INVENTORY = "inventory"


class ListItem(BaseResource):
    """A single allowed value in a configurable list of options.

    List items back the choices offered by ``list``-type custom fields (e.g.
    dropdown options) and other fixed option sets in Albert. A
    [`CustomField`][albert.resources.custom_fields.CustomField] with
    [`LIST`][albert.resources.custom_fields.FieldType.LIST] defines a list (keyed
    by ``list_type``, typically the field's name); its selectable options are
    ``ListItem`` records with a matching ``list_type``. Managed through
    [`ListsCollection`][albert.collections.lists.ListsCollection] (``client.lists``).

    Attributes
    ----------
    name : str
        The display name of the list item (the option value).
    id : str or None
        The Albert ID of the list item. Set when the item is retrieved from or
        created in Albert.
    category : ListItemCategory or None
        The category of the list item. Allowed values are ``businessDefined``,
        ``userDefined``, ``projects``, ``extensions``, and ``inventory``.
    list_type : str or None
        The list this item belongs to. For a list-type custom field this is
        typically the field's name (see
        [`CustomField`][albert.resources.custom_fields.CustomField]). For built-in
        categories the allowed values are ``projectState`` for ``projects``,
        ``extensions`` for ``extensions``, and ``casCategory`` or
        ``inventoryFunction`` for ``inventory``.

    !!! example
        ```python
        from albert.resources.lists import ListItem, ListItemCategory
        item = ListItem(name="In Progress", category=ListItemCategory.USER_DEFINED)
        ```
    """

    name: str
    id: str | None = Field(default=None, alias="albertId")
    category: ListItemCategory | None = Field(default=None)
    list_type: str | None = Field(default=None, alias="listType")

    @model_validator(mode="after")
    def validate_list_type(self) -> ListItem:
        allowed_by_category = {
            ListItemCategory.PROJECTS: {"projectState"},
            ListItemCategory.EXTENSIONS: {"extensions"},
            ListItemCategory.INVENTORY: {"casCategory", "inventoryFunction"},
        }
        if (
            self.list_type is not None
            and self.category in allowed_by_category
            and self.list_type not in allowed_by_category[self.category]
        ):
            raise ValueError(
                f"List type {self.list_type} is not allowed for category {self.category}"
            )
        return self
