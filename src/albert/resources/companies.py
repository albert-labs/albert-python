from pydantic import Field

from albert.resources.base import BaseResource


class Company(BaseResource):
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
    id: str | None = Field(default=None, alias="albertId")

    # Read-only fields
    distance: float | None = Field(default=None, exclude=True, frozen=True)
