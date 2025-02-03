from enum import Enum

from pydantic import Field

from albert.utils.types import BaseAlbertModel


class FacetType(str, Enum):
    TEXT = "text"


class FacetValue(BaseAlbertModel):
    name: str
    count: int


class FacetItem(BaseAlbertModel):
    name: str
    parameter: str
    type: FacetType
    value: list[FacetValue] = Field(default_factory=list, alias="Value")
