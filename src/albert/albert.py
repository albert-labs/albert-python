import os

from albert.collections.cas import CasCollection
from albert.collections.companies import CompanyCollection
from albert.collections.custom_fields import CustomFieldCollection
from albert.collections.custom_templates import CustomTemplatesCollection
from albert.collections.inventory import InventoryCollection
from albert.collections.lists import ListsCollection
from albert.collections.locations import LocationCollection
from albert.collections.lots import LotCollection
from albert.collections.parameter_groups import ParameterGroupCollection
from albert.collections.parameters import ParameterCollection
from albert.collections.pricings import PricingCollection
from albert.collections.projects import ProjectCollection
from albert.collections.roles import RoleCollection
from albert.collections.storage_locations import StorageLocationsCollection
from albert.collections.tags import TagCollection
from albert.collections.teams import TeamsCollection
from albert.collections.un_numbers import UnNumberCollection
from albert.collections.units import UnitCollection
from albert.collections.users import UserCollection
from albert.collections.worksheets import WorksheetCollection
from albert.session import AlbertSession
from albert.utils.client_credentials import ClientCredentials


class Albert:
    """
    Albert is the main client class for interacting with the Albert API.

    Parameters
    ----------
    base_url : str, optional
        The base URL of the Albert API (default is "https://dev.albertinventdev.com").
    token : str, optional
        The token for authentication (default is read from environment variable "ALBERT_TOKEN").
    client_credentials: ClientCredentials, optional
        The client credentials for programmatic authentication
        (default is read from the environment varaibles "ALBERT_CLIENT_ID" and "ALBERT_CLIENT_SECRET").

    Attributes
    ----------
    session : AlbertSession
        The session for API requests, with a base URL set.
    projects : ProjectCollection
        The project collection instance.
    tags : TagCollection
        The tag collection instance.
    inventory : InventoryCollection
        The inventory collection instance.
    companies : CompanyCollection
        The company collection instance.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        client_credentials: ClientCredentials | None = None,
    ):
        self.session = AlbertSession(
            base_url=base_url or os.getenv("ALBERT_BASE_URL") or "https://app.albertinvent.com",
            token=token or os.getenv("ALBERT_TOKEN"),
            client_credentials=client_credentials or ClientCredentials.from_env(),
        )

    @property
    def projects(self) -> ProjectCollection:
        return ProjectCollection(session=self.session)

    @property
    def tags(self) -> TagCollection:
        return TagCollection(session=self.session)

    @property
    def inventory(self) -> InventoryCollection:
        return InventoryCollection(session=self.session)

    @property
    def companies(self) -> CompanyCollection:
        return CompanyCollection(session=self.session)

    @property
    def lots(self) -> LotCollection:
        return LotCollection(session=self.session)

    @property
    def units(self) -> UnitCollection:
        return UnitCollection(session=self.session)

    @property
    def cas_numbers(self) -> CasCollection:
        return CasCollection(session=self.session)

    @property
    def un_numbers(self) -> UnNumberCollection:
        return UnNumberCollection(session=self.session)

    @property
    def users(self) -> UserCollection:
        return UserCollection(session=self.session)

    @property
    def locations(self) -> LocationCollection:
        return LocationCollection(session=self.session)

    @property
    def lists(self) -> ListsCollection:
        return ListsCollection(session=self.session)

    @property
    def custom_fields(self) -> CustomFieldCollection:
        return CustomFieldCollection(session=self.session)

    @property
    def roles(self) -> RoleCollection:
        return RoleCollection(session=self.session)

    @property
    def worksheets(self) -> WorksheetCollection:
        return WorksheetCollection(session=self.session)

    @property
    def templates(self) -> CustomTemplatesCollection:
        return CustomTemplatesCollection(session=self.session)

    @property
    def parameter_groups(self) -> ParameterGroupCollection:
        return ParameterGroupCollection(session=self.session)

    @property
    def parameters(self) -> ParameterCollection:
        return ParameterCollection(session=self.session)

    @property
    def storage_locations(self) -> StorageLocationsCollection:
        return StorageLocationsCollection(session=self.session)

    @property
    def pricings(self) -> PricingCollection:
        return PricingCollection(session=self.session)

    @property
    def teams(self) -> TeamsCollection:
        return TeamsCollection(session=self.session)
