from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import LastKeyCursorPaginator, PaginationMode
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import DesignCandidateSetId
from albert.resources.design_candidate_sets import DesignCandidateSet
from albert.resources.design_candidates import DesignCandidate


class DesignCandidateSetCollection(BaseCollection):
    """Access design candidate sets in the Albert platform (🧪 Beta).

    A candidate set holds the candidates a design run produced. Its ID is the
    ``result_set_id`` of the completed run. Sets are read-only.

    This collection is accessed as ``client.design_candidate_sets``.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        run = client.design_runs_v4.get_by_id(id="DSR123")
        candidates = client.design_candidate_sets.get_candidates(id=run.result_set_id)
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for candidate-set requests.

    Methods
    -------
    get_by_id(id) -> DesignCandidateSet
        Get a candidate set by its ID.
    get_candidates(id, max_items=None) -> Iterator[DesignCandidate]
        Get the candidates of a set.
    """

    _api_version = "v4"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{DesignCandidateSetCollection._api_version}/design/candidate-sets"

    @validate_call
    def get_by_id(self, *, id: DesignCandidateSetId) -> DesignCandidateSet:
        """Get a candidate set by its ID.

        !!! example
            ```python
            candidate_set = client.design_candidate_sets.get_by_id(id="DCS123")
            candidate_set.source.source_id
            # 'DSR123'
            ```

        Parameters
        ----------
        id : DesignCandidateSetId
            The candidate set ID (format ``DCS...``).

        Returns
        -------
        DesignCandidateSet
            The fully populated DesignCandidateSet.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return DesignCandidateSet(**response.json())

    @validate_call
    def get_candidates(
        self, *, id: DesignCandidateSetId, max_items: int | None = None
    ) -> Iterator[DesignCandidate]:
        """Get the candidates of a set.

        Results are returned as a lazily paginated iterator, in stored order. Each
        candidate carries its ``rank`` when the set was scored.

        !!! example
            ```python
            for candidate in client.design_candidate_sets.get_candidates(id="DCS123"):
                print(candidate.id, candidate.rank)
            ```

        Parameters
        ----------
        id : DesignCandidateSetId
            The candidate set ID (format ``DCS...``).
        max_items : int, optional
            Stop after this many candidates.

        Returns
        -------
        Iterator[DesignCandidate]
            A lazily paginated iterator over the set's candidates.
        """
        return LastKeyCursorPaginator(
            mode=PaginationMode.KEY,
            path=f"{self.base_path}/{id}/candidates",
            session=self.session,
            max_items=max_items,
            deserialize=lambda items: [DesignCandidate(**item) for item in items],
        )
