from typing import Any

from pydantic import Field, PrivateAttr

from albert.resources.base import BaseResource
from albert.resources.serialization import EntityLinkConvertible


class Company(BaseResource, EntityLinkConvertible):
    """
    Company is a Pydantic model representing a company entity.

    Attributes
    ----------
    name : str
        The name of the company.
    id : str | None
        The Albert ID of the company. Set when the company is retrieved from Albert.
    distance : float | None
        The scores of a company in a search result, optional. Read-only.
    """

    name: str
    id: str | None = Field(None, alias="albertId")
    _distance: float | None = PrivateAttr()

    def __init__(self, **data: Any):
        super().__init__(**data)
        if "distance" in data:
            self._distance = float(data["distance"])

    @property
    def distance(self) -> float:
        return self._distance
