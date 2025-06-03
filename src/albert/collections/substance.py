import json

from albert.collections.base import BaseCollection
from albert.resources.substance import SubstanceInfo, SubstanceResponse
from albert.session import AlbertSession


class SubstanceCollection(BaseCollection):
    """
    SubstanceCollection is a collection class for managing Substance entities in the Albert platform.

    Parameters
    ----------
    session : AlbertSession
        An instance of the Albert session used for API interactions.

    Attributes
    ----------
    base_path : str
        The base URL for making API requests related to substances.

    Methods
    -------
    get_by_ids(cas_ids: list[str], region: str = "US") -> list[SubstanceInfo]
        Retrieves a list of substances by their CAS IDs and optional region.
    get_by_id(cas_id: str, region: str = "US") -> SubstanceInfo
        Retrieves a single substance by its CAS ID and optional region.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{SubstanceCollection._api_version}/substances"

    def get_by_ids(
        self,
        *,
        cas_ids: list[str],
        region: str = "US",
        catch_errors: bool | None = None,
    ) -> list[SubstanceInfo]:
        """Get substances by their CAS IDs.

        If `catch_errors` is set to False, the number of substances returned
        may be less than the number of CAS IDs provided if any of the CAS IDs result in an error.

        Parameters
        ----------
        cas_ids : list[str]
            A list of CAS IDs to retrieve substances for.
        region : str, optional
            The region to filter the subastance by, by default "US"
        catch_errors : bool, optional
            Whether to catch errors for unknown CAS, by default True.

        Returns
        -------
        list[SubstanceInfo]
            A list of substances with the given CAS IDs.
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
    ) -> SubstanceInfo:
        """
        Get a substance by its CAS ID.

        Parameters
        ----------
        cas_id : str
            The CAS ID of the substance to retrieve.
        region : str, optional
            The region to filter the substance by, by default "US".
        catch_errors : bool, optional
            Whether to catch errors for unknown CAS, by default False.

        Returns
        -------
        SubstanceInfo
            The retrieved substance or raises an error if not found.
        """
        return self.get_by_ids(cas_ids=[cas_id], region=region, catch_errors=catch_errors)[0]
