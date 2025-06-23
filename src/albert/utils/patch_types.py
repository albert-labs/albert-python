from enum import Enum
from typing import Any

from pydantic import Field

from albert.utils.types import BaseAlbertModel


class PatchOperation(str, Enum):
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"


class PatchDatum(BaseAlbertModel):
    operation: str
    attribute: str
    new_value: Any | None = Field(default=None, alias="newValue")
    old_value: Any | None = Field(default=None, alias="oldValue")

    def model_dump(self, **kwargs) -> dict[str, Any]:
        # Default to exclude_unset=True to remove old/new value when not explicitly set
        kwargs.setdefault("exclude_unset", True)
        return super().model_dump(**kwargs)


class PGPatchDatum(PatchDatum):
    rowId: str | None = Field(default=None)


class DTPatchDatum(PatchDatum):
    colId: str | None = Field(default=None)


class PatchPayload(BaseAlbertModel):
    data: list[PatchDatum]

    def model_dump(self, **kwargs) -> dict[str, Any]:
        # Default to exclude_unset=True to remove old/new value when not explicitly set
        kwargs.setdefault("exclude_unset", True)
        return super().model_dump(**kwargs)


class PGPatchPayload(PatchPayload):
    """A payload for a PATCH request to update a parameter group.

    Attributes
    ----------
    data : list[PGPatchDatum]
        The data to be updated in the parameter group.
    """

    data: list[PGPatchDatum | PatchDatum] = Field(default_factory=list)


class GeneralPatchDatum(PGPatchDatum):
    colId: str | None = Field(default=None)
    actions: list[PGPatchDatum | DTPatchDatum] | None = None
    operation: str | None = Field(default=None)


class GeneralPatchPayload(PatchPayload):
    data: list[PGPatchDatum | DTPatchDatum | GeneralPatchDatum | PatchDatum] = Field(
        default_factory=list
    )
