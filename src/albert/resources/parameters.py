from enum import Enum

from pydantic import Field, PrivateAttr

from albert.resources.base import BaseResource


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

    id: str | None = Field(alias="albertId", default=None)
    name: str
    _category: ParameterCategory | None = PrivateAttr(default=None)
    _rank: int | None = PrivateAttr(default=None)

    @property
    def category(self) -> ParameterCategory:
        return self._category

    @property
    def rank(self) -> int:
        return self._rank
