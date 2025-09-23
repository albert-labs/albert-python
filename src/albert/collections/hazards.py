from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.resources.hazards import HazardStatement, HazardSymbol


class HazardsCollection(BaseCollection):
    """Collection for fetching hazard symbols and statements."""

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{self._api_version}/static"

    @validate_call
    def get_symbols(self) -> list[HazardSymbol]:
        """Fetch the list of hazard symbols."""

        response = self.session.get(f"{self.base_path}/hazardsymbols")
        response = response.json()
        symbols = response.get("HazardSymbols", []) if isinstance(response, dict) else []
        return [HazardSymbol(**symbol) for symbol in symbols]

    @validate_call
    def get_statements(self) -> list[HazardStatement]:
        """Fetch the list of hazard statements."""

        response = self.session.get(f"{self.base_path}/hazardstatements")
        response = response.json()
        return [HazardStatement(**item) for item in response]
