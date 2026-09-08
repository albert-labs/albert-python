from pydantic import Field

from albert.core.base import BaseAlbertModel


class IntervalCombinationItem(BaseAlbertModel):
    """One child-workflow interval combination on a task block.

    Returned by
    [`get_block_combinations`][albert.collections.tasks.TaskCollection.get_block_combinations].
    Use that method rather than any combinations array embedded on a task or block:
    the embedded array is empty once the block has 500 or more combinations.

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        combo = next(
            client.tasks.get_block_combinations(task_id="TASFOR1", block_id="BLK1", max_items=1)
        )
        combo.id
        # 'WFL999'
        combo.interval_barcode
        # 'OhI8ap0HY'
        ```
    """

    id: str | None = None
    """The child workflow id for this combination (format ``WFL...``)."""

    name: str | None = None
    """Display name of the combination (parameter names and values)."""

    interval_barcode: str | None = Field(default=None, alias="intervalBarcode")
    """Case-sensitive barcode for the combination. Serialized as ``intervalBarcode``."""

    interval_row_key: str | None = Field(default=None, alias="intervalRowKey")
    """Legacy ROW-chain key (e.g. ``ROW3XROW7``). Serialized as ``intervalRowKey``."""
