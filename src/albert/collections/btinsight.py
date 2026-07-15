from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import AlbertPaginator
from albert.core.session import AlbertSession
from albert.core.shared.enums import OrderBy, PaginationMode
from albert.core.shared.identifiers import BTInsightId
from albert.core.utils import ensure_list
from albert.resources.btinsight import BTInsight, BTInsightCategory, BTInsightState


class BTInsightCollection(BaseCollection):
    """Manage Breakthrough insights in the Albert platform.

    Albert Breakthrough is Albert's inverse-design / ML optimization capability. An **insight**
    (:class:`~albert.resources.btinsight.BTInsight`) is an output produced by
    Breakthrough, such as an optimizer result, impact chart, or generated
    candidate. An insight is categorized by its
    :class:`~albert.resources.btinsight.BTInsightCategory` and can trace back to the
    dataset, model session, and model it came from (``dataset_id``,
    ``model_session_id``, ``model_id``), which link to
    :class:`~albert.collections.btdataset.BTDatasetCollection` and
    :class:`~albert.collections.btmodel.BTModelCollection`.

    Insights are identified by an insight ID (format ``INS...``, e.g. ``"INS7"``).

    This collection is accessed as ``client.btinsights``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for insight requests.

    Methods
    -------
    create(insight) -> BTInsight
        Register a new insight.
    get_by_id(id) -> BTInsight
        Retrieve a single insight by its ID.
    search(...) -> Iterator[BTInsight]
        Search for insights by text, name, state, or category.
    update(insight) -> BTInsight
        Apply changes to an existing insight.
    delete(id) -> None
        Delete an insight by its ID.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert

        client = Albert()
        insight = client.btinsights.get_by_id(id="INS7")
        insight.name
        # 'Cost optimizer run'
        ```
    """

    _api_version = "v3"
    _updatable_attributes = {
        "name",
        "state",
        "metadata",
        "output_key",
        "start_time",
        "end_time",
        "total_time",
        "raw_payload",
        "content_edited",
        "payload_type",
        "registry",
    }

    def __init__(self, *, session: AlbertSession):
        """Initialize a BTInsightCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{BTInsightCollection._api_version}/btinsight"

    @validate_call
    def create(self, *, insight: BTInsight) -> BTInsight:
        """Register a new insight.

        Parameters
        ----------
        insight : BTInsight
            The insight to create. ``name`` and ``category`` are required.

        Returns
        -------
        BTInsight
            The newly created insight, populated with its assigned ID.

        Examples
        --------
        !!! example
            ```python
            from albert import Albert
            from albert.resources.btinsight import BTInsight, BTInsightCategory

            client = Albert()
            insight = BTInsight(
                name="Cost optimizer run",
                category=BTInsightCategory.OPTIMIZER,
            )
            created = client.btinsights.create(insight=insight)
            created.id
            # 'INS7'
            ```
        """
        response = self.session.post(
            self.base_path,
            json=insight.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        return BTInsight(**response.json())

    @validate_call
    def get_by_id(self, *, id: BTInsightId) -> BTInsight:
        """Retrieve a single insight by its ID.

        Parameters
        ----------
        id : BTInsightId
            The insight ID (format ``INS...``, e.g. ``"INS7"``).

        Returns
        -------
        BTInsight
            The retrieved insight.

        Examples
        --------
        !!! example
            ```python
            insight = client.btinsights.get_by_id(id="INS7")
            insight.name
            # 'Cost optimizer run'
            ```
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return BTInsight(**response.json())

    @validate_call
    def search(
        self,
        *,
        order_by: OrderBy | None = None,
        sort_by: str | None = None,
        text: str | None = None,
        name: str | list[str] | None = None,
        state: BTInsightState | list[BTInsightState] | None = None,
        category: BTInsightCategory | list[BTInsightCategory] | None = None,
        offset: int | None = None,
        max_items: int | None = None,
    ) -> Iterator[BTInsight]:
        """Search for insights matching the given filters.

        Results are returned as a lazily paginated iterator, so iterating fetches
        additional pages on demand.

        Parameters
        ----------
        order_by : OrderBy, optional
            Sort direction (ascending or descending). Default None (server order).
        sort_by : str, optional
            Field to sort by. Default None.
        text : str, optional
            Free-text query matched against insight name and related fields.
        name : str or list[str], optional
            Filter by exact insight name(s).
        state : BTInsightState or list[BTInsightState], optional
            Filter by progress state (e.g. ``Complete``, ``Error``).
        category : BTInsightCategory or list[BTInsightCategory], optional
            Filter by category (e.g. ``Optimizer``, ``Impact Chart``).
        max_items : int, optional
            Maximum number of items to return in total. If None, iterates over all
            matches.

        Returns
        -------
        Iterator[BTInsight]
            A lazily paginated iterator of matching insights.

        Examples
        --------
        !!! example
            ```python
            from albert.resources.btinsight import BTInsightCategory

            hits = client.btinsights.search(
                category=BTInsightCategory.OPTIMIZER,
                max_items=10,
            )
            for insight in hits:
                print(insight.id, insight.name)
            ```
        """
        params = {
            "offset": offset,
            "order": order_by,
            "sortBy": sort_by,
            "text": text,
            "name": ensure_list(name),
        }

        state_values = ensure_list(state)
        params["state"] = state_values if state_values else None

        category_values = ensure_list(category)
        params["category"] = category_values if category_values else None

        return AlbertPaginator(
            mode=PaginationMode.OFFSET,
            path=f"{self.base_path}/search",
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [BTInsight(**item) for item in items],
        )

    @validate_call
    def update(self, *, insight: BTInsight) -> BTInsight:
        """Update an existing insight.

        Fetch the insight (e.g. with :meth:`get_by_id`), modify the updatable
        fields on the returned object, then pass it here. Only the fields listed in
        Notes are applied; changes to other fields are ignored.

        Parameters
        ----------
        insight : BTInsight
            The insight to update. Must have a valid ``id``.

        Returns
        -------
        BTInsight
            The updated insight.

        Notes
        -----
        The following fields can be updated: ``content_edited``, ``end_time``,
        ``metadata``, ``name``, ``output_key``, ``payload_type``, ``raw_payload``,
        ``registry``, ``start_time``, ``state``, ``total_time``.

        Examples
        --------
        !!! example
            ```python
            insight = client.btinsights.get_by_id(id="INS7")
            insight.name = "Cost optimizer run (final)"
            updated = client.btinsights.update(insight=insight)
            updated.name
            # 'Cost optimizer run (final)'
            ```
        """
        path = f"{self.base_path}/{insight.id}"
        payload = self._generate_patch_payload(
            existing=self.get_by_id(id=insight.id),
            updated=insight,
            generate_metadata_diff=False,
        )
        self.session.patch(path, json=payload.model_dump(mode="json", by_alias=True))
        return self.get_by_id(id=insight.id)

    @validate_call
    def delete(self, *, id: BTInsightId) -> None:
        """Delete an insight by its ID.

        Parameters
        ----------
        id : BTInsightId
            The insight ID to delete (format ``INS...``).

        Returns
        -------
        None

        Examples
        --------
        !!! example
            ```python
            client.btinsights.delete(id="INS7")
            ```
        """
        self.session.delete(f"{self.base_path}/{id}")
