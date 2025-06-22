from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel


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


class PatchPayload(BaseAlbertModel):
    data: list[PatchDatum]

    def model_dump(self, **kwargs) -> dict[str, Any]:
        # Default to exclude_unset=True to remove old/new value when not explicitly set
        kwargs.setdefault("exclude_unset", True)
        return super().model_dump(**kwargs)


class GeneralPatchDatum(PGPatchDatum):
    colId: str | None = Field(default=None)
    actions: list[PGPatchDatum] | None = None
    operation: str | None = Field(default=None)
