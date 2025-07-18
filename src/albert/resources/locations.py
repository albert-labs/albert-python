from pydantic import Field

from albert.core.shared.models.base import BaseResource


class Location(BaseResource):
    """A location in Albert.

    Attributes
    ----------
    name : str
        The name of the location.
    id : str | None
        The Albert ID of the location. Set when the location is retrieved from Albert.
    latitude : float
        The latitude of the location.
    longitude : float
        The longitude of the location.
    address : str
        The address of the location.
    country : str | None
        The country code of the location. Must be two characters long.
    """

    name: str
    id: str | None = Field(None, alias="albertId")
    latitude: float = Field()
    longitude: float = Field()
    address: str
    country: str | None = Field(None, max_length=2, min_length=2)
