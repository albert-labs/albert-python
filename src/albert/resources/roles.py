from typing import Any

from pydantic import Field

from albert.core.shared.models.base import BaseResource


class Role(BaseResource):
    """A role in Albert. Roles are not currently creatable via the SDK.

    Attributes
    ----------
    id : str | None
        The Albert ID of the role.
    name : str
        The name of the role.
    policies : list[Any] | None
        The policies associated with the role.
    tenant : str
        The tenant ID the role belongs to.
    visibility : bool | None
        Whether the role is visible to users.
    """

    id: str | None = Field(default=None, alias="albertId")
    name: str
    policies: list[Any] | None = Field(default=None, alias="Policies")
    tenant: str
    visibility: bool | None = Field(default=None)
