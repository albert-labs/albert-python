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

    def get_by_ids(self, *, cas_ids: list[str], region: str = "US") -> list[SubstanceInfo]:
        """Get substances by their CAS IDs.

        Parameters
        ----------
        cas_ids : list[str]
            A list of CAS IDs to retrieve substances for.
        region : str, optional
            The region to filter the subastance by, by default "US"

        Returns
        -------
        list[SubstanceInfo]
            A list of substances with the given CAS IDs.
        """
        url = f"{self.base_path}"
        response = self.session.get(url, params={"casIDs": ",".join(cas_ids), "region": region})
        return SubstanceResponse.model_validate(response.json()).substances

    def get_by_id(self, *, cas_id: str, region: str = "US") -> SubstanceInfo:
        """
        Get a substance by its CAS ID.

        Parameters
        ----------
        cas_id : str
            The CAS ID of the substance to retrieve.

        Returns
        -------
        SubstanceInfo
            The retrieved substance or raises an error if not found.
        """
        return self.get_by_ids(cas_ids=[cas_id], region=region)[0]
