from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.pagination import LastKeyCursorPaginator, PaginationMode
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import DesignCandidateId, DesignCandidateSetId
from albert.resources.design_candidates import DesignCandidate


class DesignCandidateCollection(BaseCollection):
    """Read design candidates in the Albert platform (🧪 Beta).

    A candidate is one formulation a design run proposed, with its sampled inputs and,
    where the run produced them, its predictions and score. Candidates are read-only.

    This collection is accessed as ``client.design_candidates``.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        candidate = client.design_candidates.get_by_id(id="DCN123")
        candidate.predictions
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for candidate requests.

    Methods
    -------
    get_by_id(id) -> DesignCandidate
        Get a candidate by its ID.
    get_all(candidate_set_id, max_items=None) -> Iterator[DesignCandidate]
        Get the candidates of a set.
    """

    _api_version = "v4"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{DesignCandidateCollection._api_version}/design/candidates"

    @validate_call
    def get_by_id(self, *, id: DesignCandidateId) -> DesignCandidate:
        """Get a candidate by its ID.

        ``rank`` is not returned here; it is only derived when listing a set's candidates.

        !!! example
            ```python
            candidate = client.design_candidates.get_by_id(id="DCN123")
            ```

        Parameters
        ----------
        id : DesignCandidateId
            The candidate ID (format ``DCN...``).

        Returns
        -------
        DesignCandidate
            The candidate.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return DesignCandidate(**response.json())

    @validate_call
    def get_all(
        self, *, candidate_set_id: DesignCandidateSetId, max_items: int | None = None
    ) -> Iterator[DesignCandidate]:
        """Get the candidates of a set.

        Results are returned as a lazily paginated iterator, in stored order. Each
        candidate carries its ``rank`` when the set was scored.

        !!! example
            ```python
            for candidate in client.design_candidates.get_all(candidate_set_id="DCS123"):
                print(candidate.id, candidate.rank)
            ```

        Parameters
        ----------
        candidate_set_id : DesignCandidateSetId
            The candidate set (format ``DCS...``) whose candidates to list.
        max_items : int, optional
            Stop after this many candidates.

        Returns
        -------
        Iterator[DesignCandidate]
            A lazily paginated iterator over the set's candidates.
        """
        return LastKeyCursorPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params={"candidateSetId": candidate_set_id},
            max_items=max_items,
            deserialize=lambda items: [DesignCandidate(**item) for item in items],
        )
