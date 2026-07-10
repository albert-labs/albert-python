from typing import Any

from pydantic import Field

from albert.core.shared.models.base import BaseResource


class Role(BaseResource):
    """A named set of access permissions within a tenant.

    A role bundles policies that determine what a holder is allowed to do. Roles
    are assigned to users (:class:`~albert.resources.users.User`) and referenced
    by entity ACLs. Roles are typically read from Albert rather than built by
    hand.

    Attributes
    ----------
    name : str
        The display name of the role.
    id : str | None
        The Albert ID of the role. Role IDs may contain ``#`` characters. Set
        once the role is retrieved from Albert.
    policies : list[Any] | None
        The policies (permission rules) associated with the role.
    tenant : str
        The ID of the tenant the role belongs to.
    visibility : bool | None
        Whether the role is visible in the platform's role listings.
    """

    id: str | None = Field(default=None, alias="albertId")
    name: str
    policies: list[Any] | None = Field(default=None, alias="Policies")
    tenant: str
    visibility: bool | None = Field(default=None)
