from typing import Any

from pydantic import Field

from albert.core.shared.models.base import BaseResource


class Role(BaseResource):
    """A role in Albert. Note: Roles are not currently creatable via the SDK.

    Attributes
    ----------
    name : str
        The name of the role.
    id : str
        The Albert ID of the role. Set when the role is retrieved from Albert.
    policies : list[Any] | None
        The policies associated with the role.
    tenant : str
        The tenant ID of the role.
    """

    id: str | None = Field(default=None, alias="albertId")
    name: str
    policies: list[Any] | None = Field(default=None)
    tenant: str
