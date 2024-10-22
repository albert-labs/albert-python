from typing import Any

from pydantic import Field

from albert.resources.base import BaseResource, EntityLinkConvertible, SecurityClass
from albert.resources.users import User


class Team(BaseResource, EntityLinkConvertible):
    name: str = Field(min_length=1, max_length=255)
    team_class: SecurityClass = SecurityClass.RESTRICTED
    user: list[User] | None = Field(default=None)
    acl: None
