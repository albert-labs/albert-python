from enum import Enum

from pydantic import Field

from albert.core.base import BaseAlbertModel


class FacetType(str, Enum):
    TEXT = "text"


class FacetValue(BaseAlbertModel):
    """A single value within a search facet, with its occurrence count."""

    name: str
    """The facet value label."""

    count: int
    """The number of results that have this facet value."""


class FacetItem(BaseAlbertModel):
    """A search facet grouping related filter values."""

    name: str
    """The display name of the facet."""

    parameter: str
    """The query parameter name used to filter by this facet."""

    type: FacetType
    """The data type of the facet values."""

    value: list[FacetValue] = Field(default_factory=list, alias="Value")
    """The individual values within this facet and their counts."""
