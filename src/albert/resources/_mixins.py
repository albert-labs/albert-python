from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import PrivateAttr
from typing_extensions import Self  # available in `typing` from Python 3.11

from albert.exceptions import AlbertException

if TYPE_CHECKING:
    from albert.collections.base import BaseCollection

T = TypeVar("T")


class HydrationMixin(Generic[T]):
    _collection: BaseCollection | None = PrivateAttr(default=None)

    def _bind_collection(self, collection: BaseCollection) -> Self:
        self._collection = collection
        return self

    def hydrate(self) -> T:
        if not self._collection:
            raise RuntimeError("No collection is bound to this resource.")
        if not hasattr(self._collection, "get_by_id"):
            raise AlbertException("This resource does not support hydration.")
        if not hasattr(self, "id") or self.id is None:
            raise ValueError("Resource must have a non-null `id` to hydrate.")
        return self._collection.get_by_id(id=self.id)
