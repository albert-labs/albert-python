from typing import Any

from pydantic import Field

from albert.core.shared.models.base import BaseResource


class Role(BaseResource):
    """A named set of access permissions within a tenant.

    A role bundles policies that determine what a holder is allowed to do. Roles
    are assigned to users ([`User`][albert.resources.users.User]) and referenced
    by entity ACLs. Roles are typically read from Albert rather than built by
    hand."""

    id: str | None = Field(default=None, alias="albertId")
    """The Albert ID of the role. Role IDs may contain ``#`` characters. Set once the role is retrieved from Albert."""

    name: str
    """The display name of the role."""

    policies: list[Any] | None = Field(default=None, alias="Policies")
    """The policies (permission rules) associated with the role."""

    tenant: str
    """The ID of the tenant the role belongs to."""

    visibility: bool | None = Field(default=None)
    """Whether the role is visible in the platform's role listings."""
