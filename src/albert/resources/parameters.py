from enum import Enum

from pydantic import Field

from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import MetadataItem


class ParameterCategory(str, Enum):
    """The category of a parameter"""

    NORMAL = "Normal"
    SPECIAL = "Special"


class Parameter(BaseResource):
    """A parameter definition in Albert.

    Parameters are named variables used in workflows and parameter groups to describe
    experimental conditions. Names must be unique.

    Attributes
    ----------
    name : str
        The name of the parameter. Must be unique across the tenant.
    id : str | None
        The Albert ID of the parameter.
    metadata : dict[str, MetadataItem] | None
        Custom metadata attached to the parameter.
    category : ParameterCategory | None
        The parameter category (Normal or Special). Read-only.
    rank : int | None
        The sort rank returned from a search. Read-only.
    required : bool | None
        Whether the parameter is required in its context. Read-only.
    """

    name: str
    id: str | None = Field(alias="albertId", default=None)
    metadata: dict[str, MetadataItem] | None = Field(alias="Metadata", default=None)

    # Read-only fields
    category: ParameterCategory | None = Field(default=None, exclude=True, frozen=True)
    rank: int | None = Field(default=None, exclude=True, frozen=True)
    required: bool | None = Field(default=None, exclude=True)
