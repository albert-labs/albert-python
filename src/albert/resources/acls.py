from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.models.base import BaseResource


class AccessControlLevel(str, Enum):
    """Access control levels you can grant users."""

    PROJECT_OWNER = "ProjectOwner"
    PROJECT_EDITOR = "ProjectEditor"
    PROJECT_VIEWER = "ProjectViewer"
    PROJECT_ALL_TASKS = "ProjectAllTask"
    PROJECT_STRICT_VIEWER = "ProjectStrictViewer"
    PROJECT_PROPERTY_TASKS = "ProjectPropertyTask"
    INVENTORY_OWNER = "InventoryOwner"
    INVENTORY_VIEWER = "InventoryViewer"
    CUSTOM_TEMPLATE_OWNER = "CustomTemplateOwner"
    CUSTOM_TEMPLATE_VIEWER = "CustomTemplateViewer"
    CAS_FULL_ACCESS = "CASFullAccess"


class ACL(BaseAlbertModel):
    """A single access rule for a user.

    Attributes
    ----------
    id : str
        The user or team this rule applies to.
    fgc : AccessControlLevel | None
        The access level for that user or team.
    """

    id: str = Field(description="The id of the user for which this ACL applies")
    fgc: AccessControlLevel | None = Field(
        default=None, description="The Fine-Grain Control Level"
    )


class ACLContainer(BaseResource):
    """Access settings with a default class and a list of rules.

    Attributes
    ----------
    acl_class : str | None
        The default access class (for example, "restricted" or "confidential").
    fgclist : list[ACL] | None
        Specific access rules for users or teams.
    """

    acl_class: str | None = Field(default=None, alias="class")
    fgclist: list[ACL] | None = Field(default=None, alias="fgclist")
