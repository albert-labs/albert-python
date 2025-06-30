from enum import Enum

from pydantic import Field

from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem


class ParameterCategory(str, Enum):
    """The category of a parameter"""

    NORMAL = "Normal"
    SPECIAL = "Special"


class Parameter(BaseResource):
    """A parameter in Albert.

    Attributes
    ----------
    name : str
        The name of the parameter. Names must be unique.
    id : str | None
        The Albert ID of the parameter. Set when the parameter is retrieved from Albert.
    category : ParameterCategory
        The category of the parameter. Allowed values are `Normal` and `Special`. Read-only.
    rank : int
        The rank of the returned parameter. Read-only.
    """

    name: str
    id: str | None = Field(alias="albertId", default=None)
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)

    # Read-only fields
    category: ParameterCategory | None = Field(default=None, exclude=True, frozen=True)
    rank: int | None = Field(default=None, exclude=True, frozen=True)
