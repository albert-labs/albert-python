import pytest

from albert.core.base import BaseAlbertModel
from albert.exceptions import AlbertException
from albert.resources._mixins import HydrationMixin


class _FakeSearchItem(BaseAlbertModel, HydrationMixin["_FakeSearchItem"]):
    id: str | None = None
    name: str | None = None


class _FakeCollectionWithGetById:
    """A minimal stub exposing only get_by_id, no session/I/O."""

    def __init__(self, result):
        self.result = result
        self.calls = []

    def get_by_id(self, *, id: str):
        self.calls.append(id)
        return self.result


class _FakeCollectionWithoutGetById:
    """A stub that does not support hydration."""


def test_bind_collection_returns_self():
    """Test that _bind_collection binds the collection and returns the same instance."""
    item = _FakeSearchItem(id="ITM1")
    collection = _FakeCollectionWithGetById(result="hydrated")

    bound = item._bind_collection(collection)

    assert bound is item
    assert item._collection is collection


def test_hydrate_without_bound_collection_raises_runtime_error():
    """Test that hydrate raises RuntimeError when no collection was ever bound."""
    item = _FakeSearchItem(id="ITM1")

    with pytest.raises(RuntimeError, match="No collection is bound"):
        item.hydrate()


def test_hydrate_with_collection_missing_get_by_id_raises_albert_exception():
    """Test that hydrate raises AlbertException when the bound collection can't hydrate."""
    item = _FakeSearchItem(id="ITM1")
    item._bind_collection(_FakeCollectionWithoutGetById())

    with pytest.raises(AlbertException, match="does not support hydration"):
        item.hydrate()


def test_hydrate_without_id_raises_value_error():
    """Test that hydrate raises ValueError when the resource has no non-null id."""
    item = _FakeSearchItem(id=None)
    item._bind_collection(_FakeCollectionWithGetById(result="hydrated"))

    with pytest.raises(ValueError, match="non-null `id`"):
        item.hydrate()


def test_hydrate_calls_get_by_id_with_the_resource_id_and_returns_result():
    """Test that hydrate delegates to the bound collection's get_by_id with this resource's id."""
    item = _FakeSearchItem(id="ITM1")
    collection = _FakeCollectionWithGetById(result="hydrated-item")
    item._bind_collection(collection)

    result = item.hydrate()

    assert result == "hydrated-item"
    assert collection.calls == ["ITM1"]
