from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.resources.hazards import HazardStatement, HazardSymbol


class HazardsCollection(BaseCollection):
    """Fetch the platform's reference lists of GHS hazard symbols and statements.

    Hazards are GHS (Globally Harmonized System) classifications used to describe
    the dangers of a substance. This collection returns the two static reference
    lists Albert maintains: the hazard pictogram symbols and the hazard
    statements. These are the master lists you draw from when classifying
    materials; the specific hazards recorded on a substance appear on its CAS
    record (see [`Hazard`][albert.resources.cas.Hazard]).

    This collection is read-only and accessed as ``client.hazards``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for the static reference endpoints.

    Methods
    -------
    get_symbols() -> list[HazardSymbol]
        Fetch all available hazard pictogram symbols.
    get_statements() -> list[HazardStatement]
        Fetch all available hazard statements.

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        symbols = client.hazards.get_symbols()
        [s.name for s in symbols]
        ```
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a HazardsCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{self._api_version}/static"

    @validate_call
    def get_symbols(self) -> list[HazardSymbol]:
        """Fetch all available hazard pictogram symbols.

        Returns
        -------
        list[HazardSymbol]
            The full reference list of hazard symbols.

        !!! example
            ```python
            symbols = client.hazards.get_symbols()
            symbols[0].name
            ```
        """

        response = self.session.get(f"{self.base_path}/hazardsymbols")
        response = response.json()
        symbols = response.get("HazardSymbols", []) if isinstance(response, dict) else []
        return [HazardSymbol(**symbol) for symbol in symbols]

    @validate_call
    def get_statements(self) -> list[HazardStatement]:
        """Fetch all available hazard statements.

        Returns
        -------
        list[HazardStatement]
            The full reference list of hazard statements.

        !!! example
            ```python
            statements = client.hazards.get_statements()
            statements[0].name
            ```
        """

        response = self.session.get(f"{self.base_path}/hazardstatements")
        response = response.json()
        return [HazardStatement(**item) for item in response]
