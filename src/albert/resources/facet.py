from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel


class FacetType(str, Enum):
    TEXT = "text"


class FacetValue(BaseAlbertModel):
    """A single value within a search facet, with its occurrence count.

    Attributes
    ----------
    name : str
        The facet value label.
    count : int
        The number of results that have this facet value.
    """

    name: str
    count: int


class FacetItem(BaseAlbertModel):
    """A search facet grouping related filter values.

    Attributes
    ----------
    name : str
        The display name of the facet.
    parameter : str
        The query parameter name used to filter by this facet.
    type : FacetType
        The data type of the facet values.
    value : list[FacetValue]
        The individual values within this facet and their counts.
    """

    name: str
    parameter: str
    type: FacetType
    value: list[FacetValue] = Field(default_factory=list, alias="Value")
