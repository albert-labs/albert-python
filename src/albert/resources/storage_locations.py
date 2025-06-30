from pydantic import Field

from albert.core.shared.models.base import BaseResource
from albert.core.shared.types import SerializeAsEntityLink
from albert.resources.locations import Location


class StorageLocation(BaseResource):
    """A storage location entity. For example, a specific flammables cabinet or a storage room.

    Attributes
    ----------
    name : str
        The name of the storage location.
    id : str | None
        The Albert ID of the storage location. Set when the storage location is retrieved from Albert.
    location : Location
        The location entity link of the storage location.
    """

    name: str = Field(alias="name", min_length=2, max_length=255)
    id: str | None = Field(alias="albertId", default=None)
    location: SerializeAsEntityLink[Location] = Field(alias="Location")
