import json

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.resources.substance import SubstanceInfo, SubstanceResponse


class SubstanceCollection(BaseCollection):
    """Look up regulatory and hazard information for chemical substances.

    A Substance is the regulatory/compliance profile of a chemical, keyed by its
    CAS number. Each :class:`~albert.resources.substance.SubstanceInfo` bundles
    the data Albert holds for that chemical, including GHS hazard
    classifications, toxicity and ecotoxicity data, exposure limits, physical
    properties, and membership on regulatory lists across many jurisdictions.
    Results can be scoped to a region, since regulatory status varies by country.

    Substances are read-only reference data: this collection only retrieves
    information and does not create or modify it. They are addressed by CAS
    number (e.g. ``"64-17-5"``) rather than by an Albert ID, and relate to
    :class:`~albert.resources.cas.Cas` records used elsewhere in the platform.

    This collection is accessed as ``client.substances``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for substance requests.

    Methods
    -------
    get_by_ids(cas_ids, region="US", catch_errors=None) -> list[SubstanceInfo]
        Retrieve regulatory information for several CAS numbers at once.
    get_by_id(cas_id, region="US", catch_errors=None) -> SubstanceInfo | None
        Retrieve regulatory information for a single CAS number.

    Examples
    --------
    !!! example
        ```python
        from albert import Albert

        client = Albert()
        substance = client.substances.get_by_id(cas_id="64-17-5")
        substance.cas_id
        # '64-17-5'
        ```
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a SubstanceCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{SubstanceCollection._api_version}/substances"

    def get_by_ids(
        self,
        *,
        cas_ids: list[str],
        region: str = "US",
        catch_errors: bool | None = None,
    ) -> list[SubstanceInfo]:
        """Retrieve regulatory information for several CAS numbers at once.

        For a single CAS number, use :meth:`get_by_id`.

        Parameters
        ----------
        cas_ids : list[str]
            The CAS numbers to retrieve substances for (e.g. ``["64-17-5"]``).
        region : str, optional
            The region to scope regulatory status to. Defaults to ``"US"``.
        catch_errors : bool, optional
            How to handle CAS numbers that cannot be resolved. When True, such
            errors are absorbed and those substances are simply omitted from the
            result, so fewer substances may be returned than CAS numbers
            requested. When None (default), the server default applies.

        Returns
        -------
        list[SubstanceInfo]
            The substances found for the given CAS numbers.

        Examples
        --------
        !!! example
            ```python
            from albert import Albert

            client = Albert()
            substances = client.substances.get_by_ids(cas_ids=["64-17-5", "67-64-1"])
            [s.cas_id for s in substances]
            # ['64-17-5', '67-64-1']
            ```
        """
        params = {
            "casIDs": ",".join(cas_ids),
            "region": region,
            "catchErrors": json.dumps(catch_errors) if catch_errors is not None else None,
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = self.session.get(self.base_path, params=params)
        return SubstanceResponse.model_validate(response.json()).substances

    def get_by_id(
        self,
        *,
        cas_id: str,
        region: str = "US",
        catch_errors: bool | None = None,
    ) -> SubstanceInfo | None:
        """Retrieve regulatory information for a single CAS number.

        To look up several CAS numbers in one call, use :meth:`get_by_ids`.

        Parameters
        ----------
        cas_id : str
            The CAS number of the substance to retrieve (e.g. ``"64-17-5"``).
        region : str, optional
            The region to scope regulatory status to. Defaults to ``"US"``.
        catch_errors : bool, optional
            How to handle a CAS number that cannot be resolved. When True, the
            error is absorbed and None is returned instead. When None (default),
            the server default applies.

        Returns
        -------
        SubstanceInfo or None
            The substance for the given CAS number, or None if it is not found.

        Examples
        --------
        !!! example
            ```python
            from albert import Albert

            client = Albert()
            substance = client.substances.get_by_id(cas_id="64-17-5")
            substance.is_known
            # True
            ```
        """
        results = self.get_by_ids(cas_ids=[cas_id], region=region, catch_errors=catch_errors)
        return results[0] if results else None
