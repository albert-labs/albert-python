from __future__ import annotations

import os

from pydantic import SecretStr

from albert.collections.activities import ActivityCollection
from albert.collections.attachments import AttachmentCollection
from albert.collections.batch_data import BatchDataCollection
from albert.collections.btdataset import BTDatasetCollection
from albert.collections.btinsight import BTInsightCollection
from albert.collections.btmodel import BTModelCollection, BTModelSessionCollection
from albert.collections.cas import CasCollection
from albert.collections.chat_flags import ChatFlagCollection
from albert.collections.chat_folders import ChatFolderCollection
from albert.collections.chat_messages import ChatMessageCollection
from albert.collections.chat_sessions import ChatSessionCollection
from albert.collections.companies import CompanyCollection
from albert.collections.custom_fields import CustomFieldCollection
from albert.collections.custom_templates import CustomTemplatesCollection
from albert.collections.data_columns import DataColumnCollection
from albert.collections.data_templates import DataTemplateCollection
from albert.collections.entity_types import EntityTypeCollection
from albert.collections.files import FileCollection
from albert.collections.hazards import HazardsCollection
from albert.collections.inventory import InventoryCollection
from albert.collections.links import LinksCollection
from albert.collections.lists import ListsCollection
from albert.collections.locations import LocationCollection
from albert.collections.lots import LotCollection
from albert.collections.notebooks import NotebookCollection
from albert.collections.notes import NotesCollection
from albert.collections.parameter_groups import ParameterGroupCollection
from albert.collections.parameters import ParameterCollection
from albert.collections.pricings import PricingCollection
from albert.collections.product_design import ProductDesignCollection
from albert.collections.projects import ProjectCollection
from albert.collections.property_data import PropertyDataCollection
from albert.collections.report_templates import ReportTemplateCollection
from albert.collections.reports import ReportCollection
from albert.collections.roles import RoleCollection
from albert.collections.smart_datasets import SmartDatasetCollection
from albert.collections.storage_classes import StorageClassesCollection
from albert.collections.storage_locations import StorageLocationsCollection
from albert.collections.substance import SubstanceCollection
from albert.collections.substance_v4 import SubstanceCollectionV4
from albert.collections.synthesis import SynthesisCollection
from albert.collections.tags import TagCollection
from albert.collections.targets import TargetCollection
from albert.collections.tasks import TaskCollection
from albert.collections.teams import TeamCollection
from albert.collections.un_numbers import UnNumberCollection
from albert.collections.units import UnitCollection
from albert.collections.users import UserCollection
from albert.collections.workflows import WorkflowCollection
from albert.collections.worksheets import WorksheetCollection
from albert.core.async_session import AsyncAlbertSession
from albert.core.auth.credentials import AlbertClientCredentials
from albert.core.auth.sso import AlbertSSOClient
from albert.core.session import AlbertSession
from albert.utils._auth import default_albert_base_url


class Albert:
    """
    Main client for interacting with the Albert API.

    This class manages authentication and access to API resource collections.
    It supports token-based, SSO, and client credentials authentication via a unified interface.

    Parameters
    ----------
    base_url : str, optional
        The base URL of the Albert API. If not provided, the URL from ``auth_manager`` is used
        when available, otherwise the ``ALBERT_BASE_URL`` environment variable or
        "https://app.albertinvent.com".
    token : str, optional
        A static token for authentication. If provided, it overrides any `auth_manager`.
        Defaults to the "ALBERT_TOKEN" environment variable.
    auth_manager : AlbertClientCredentials | AlbertSSOClient, optional
        An authentication manager for OAuth2-based authentication flows.
        Ignored if `token` is provided.
    retries : int, optional
        Maximum number of retries for failed HTTP requests.
    session : AlbertSession, optional
        A fully configured session instance. If provided, `base_url`, `token`, and `auth_manager`
        are all ignored.

    Attributes
    ----------
    session : AlbertSession
        The internal session used for authenticated requests.
    projects : ProjectCollection
        Access to project-related API methods.
    tags : TagCollection
        Access to tag-related API methods.
    inventory : InventoryCollection
        Access to inventory-related API methods.
    companies : CompanyCollection
        Access to company-related API methods.

    Helpers
    -------------------
    - `from_token` — Create a client using a static token.
    - `from_sso` — Create a client using interactive browser-based SSO login.
    - `from_client_credentials` — Create a client using OAuth2 client credentials.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        auth_manager: AlbertClientCredentials | AlbertSSOClient | None = None,
        retries: int | None = None,
        session: AlbertSession | None = None,
    ):
        if auth_manager and base_url and base_url != auth_manager.base_url:
            raise ValueError("`base_url` must match the URL used by the auth manager.")

        resolved_base_url = (
            base_url
            or (auth_manager.base_url if auth_manager else None)
            or default_albert_base_url()
        )

        self.session = session or AlbertSession(
            base_url=resolved_base_url,
            token=token or os.getenv("ALBERT_TOKEN"),
            auth_manager=auth_manager,
            retries=retries,
        )

    @classmethod
    def from_token(cls, *, base_url: str | None, token: str) -> Albert:
        """Create an Albert client using a static token for authentication."""
        return cls(base_url=base_url, token=token)

    @classmethod
    def from_sso(
        cls,
        *,
        base_url: str | None,
        email: str,
        port: int = 5000,
        tenant_id: str | None = None,
        retries: int | None = None,
    ) -> Albert:
        """Create an Albert client using interactive OAuth2 SSO login."""
        resolved_base_url = base_url or default_albert_base_url()
        oauth = AlbertSSOClient(base_url=resolved_base_url, email=email)
        oauth.authenticate(minimum_port=port, tenant_id=tenant_id)
        return cls(auth_manager=oauth, retries=retries)

    @classmethod
    def from_client_credentials(
        cls,
        *,
        base_url: str | None,
        client_id: str,
        client_secret: str,
        retries: int | None = None,
    ) -> Albert:
        """Create an Albert client using client credentials authentication."""
        resolved_base_url = base_url or default_albert_base_url()
        creds = AlbertClientCredentials(
            id=client_id,
            secret=SecretStr(client_secret),
            base_url=resolved_base_url,
        )
        return cls(auth_manager=creds, retries=retries)

    @property
    def projects(self) -> ProjectCollection:
        return ProjectCollection(session=self.session)

    @property
    def activities(self) -> ActivityCollection:
        return ActivityCollection(session=self.session)

    @property
    def attachments(self) -> AttachmentCollection:
        return AttachmentCollection(session=self.session)

    @property
    def tags(self) -> TagCollection:
        return TagCollection(session=self.session)

    @property
    def teams(self) -> TeamCollection:
        return TeamCollection(session=self.session)

    @property
    def targets(self) -> TargetCollection:
        return TargetCollection(session=self.session)

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
    def synthesis(self) -> SynthesisCollection:
        return SynthesisCollection(session=self.session)

    @property
    def units(self) -> UnitCollection:
        return UnitCollection(session=self.session)

    @property
    def cas_numbers(self) -> CasCollection:
        return CasCollection(session=self.session)

    @property
    def data_columns(self) -> DataColumnCollection:
        return DataColumnCollection(session=self.session)

    @property
    def data_templates(self) -> DataTemplateCollection:
        return DataTemplateCollection(session=self.session)

    @property
    def un_numbers(self) -> UnNumberCollection:
        return UnNumberCollection(session=self.session)

    @property
    def users(self) -> UserCollection:
        return UserCollection(session=self.session)

    @property
    def entity_types(self) -> EntityTypeCollection:
        return EntityTypeCollection(session=self.session)

    @property
    def locations(self) -> LocationCollection:
        return LocationCollection(session=self.session)

    @property
    def lists(self) -> ListsCollection:
        return ListsCollection(session=self.session)

    @property
    def notebooks(self) -> NotebookCollection:
        return NotebookCollection(session=self.session)

    @property
    def notes(self) -> NotesCollection:
        return NotesCollection(session=self.session)

    @property
    def custom_fields(self) -> CustomFieldCollection:
        return CustomFieldCollection(session=self.session)

    @property
    def reports(self) -> ReportCollection:
        return ReportCollection(session=self.session)

    @property
    def report_templates(self) -> ReportTemplateCollection:
        return ReportTemplateCollection(session=self.session)

    @property
    def roles(self) -> RoleCollection:
        return RoleCollection(session=self.session)

    @property
    def worksheets(self) -> WorksheetCollection:
        return WorksheetCollection(session=self.session)

    @property
    def tasks(self) -> TaskCollection:
        return TaskCollection(session=self.session)

    @property
    def custom_templates(self) -> CustomTemplatesCollection:
        return CustomTemplatesCollection(session=self.session)

    @property
    def parameter_groups(self) -> ParameterGroupCollection:
        return ParameterGroupCollection(session=self.session)

    @property
    def parameters(self) -> ParameterCollection:
        return ParameterCollection(session=self.session)

    @property
    def property_data(self) -> PropertyDataCollection:
        return PropertyDataCollection(session=self.session)

    @property
    def product_design(self) -> ProductDesignCollection:
        return ProductDesignCollection(session=self.session)

    @property
    def storage_locations(self) -> StorageLocationsCollection:
        return StorageLocationsCollection(session=self.session)

    @property
    def pricings(self) -> PricingCollection:
        return PricingCollection(session=self.session)

    @property
    def files(self) -> FileCollection:
        return FileCollection(session=self.session)

    @property
    def workflows(self) -> WorkflowCollection:
        return WorkflowCollection(session=self.session)

    @property
    def btdatasets(self) -> BTDatasetCollection:
        return BTDatasetCollection(session=self.session)

    @property
    def btmodelsessions(self) -> BTModelSessionCollection:
        return BTModelSessionCollection(session=self.session)

    @property
    def btmodels(self) -> BTModelCollection:
        return BTModelCollection(session=self.session)

    @property
    def btinsights(self) -> BTInsightCollection:
        return BTInsightCollection(session=self.session)

    @property
    def smart_datasets(self) -> SmartDatasetCollection:
        return SmartDatasetCollection(session=self.session)

    @property
    def substances(self) -> SubstanceCollection:
        return SubstanceCollection(session=self.session)

    @property
    def substances_v4(self) -> SubstanceCollectionV4:
        return SubstanceCollectionV4(session=self.session)

    @property
    def links(self) -> LinksCollection:
        return LinksCollection(session=self.session)

    @property
    def batch_data(self) -> BatchDataCollection:
        return BatchDataCollection(session=self.session)

    @property
    def storage_classes(self) -> StorageClassesCollection:
        return StorageClassesCollection(session=self.session)

    @property
    def hazards(self) -> HazardsCollection:
        return HazardsCollection(session=self.session)


class AsyncAlbert:
    """
    Async client for interacting with the Albert chat API (🧪Beta).

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    Uses ``httpx.AsyncClient`` under the hood and must be closed when no longer
    needed — either by calling ``await client.aclose()`` or by using the client
    as an async context manager (``async with AsyncAlbert(...) as client``).

    Parameters
    ----------
    base_url : str, optional
        The base URL of the Albert API. Falls back to the ``ALBERT_BASE_URL``
        environment variable or "https://app.albertinvent.com".
    token : str, optional
        A static JWT token. Ignored when ``auth_manager`` is provided.
        Defaults to the ``ALBERT_TOKEN`` environment variable.
    auth_manager : AlbertClientCredentials | AlbertSSOClient, optional
        An authentication manager for OAuth2-based token refresh.
        Ignored if ``token`` is provided.
    session : AsyncAlbertSession, optional
        A fully configured async session. When provided, ``base_url``, ``token``,
        and ``auth_manager`` are all ignored.

    Attributes
    ----------
    session : AsyncAlbertSession
        The internal async session used for authenticated requests.
    chat_sessions : ChatSessionCollection
        Access to chat session API methods.
    chat_messages : ChatMessageCollection
        Access to chat message API methods.
    chat_folders : ChatFolderCollection
        Access to chat folder API methods.
    chat_flags : ChatFlagCollection
        Access to chat flag API methods.

    Examples
    --------
    One-off usage with an async context manager:

    ```python
    async with AsyncAlbert(base_url=..., token=...) as client:
        sessions = [s async for s in client.chat_sessions.get_all()]
    ```

    Long-lived client via FastAPI lifespan:

    ```python
    @asynccontextmanager
    async def lifespan(app):
        app.state.albert = AsyncAlbert(base_url=..., token=...)
        yield
        await app.state.albert.aclose()
    ```
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        auth_manager: AlbertClientCredentials | AlbertSSOClient | None = None,
        session: AsyncAlbertSession | None = None,
    ):
        if session is not None:
            self.session = session
            return

        if auth_manager and base_url and base_url != auth_manager.base_url:
            raise ValueError("`base_url` must match the URL used by the auth manager.")

        resolved_base_url = (
            base_url
            or (auth_manager.base_url if auth_manager else None)
            or default_albert_base_url()
        )

        self.session = AsyncAlbertSession(
            base_url=resolved_base_url,
            token=token or os.getenv("ALBERT_TOKEN"),
            auth_manager=auth_manager,
        )

    @classmethod
    def from_token(cls, *, base_url: str | None = None, token: str) -> AsyncAlbert:
        """
        Create an AsyncAlbert client using a static token for authentication.

        Parameters
        ----------
        base_url : str | None, optional
            The base URL of the Albert API. Falls back to the ``ALBERT_BASE_URL``
            environment variable or "https://app.albertinvent.com".
        token : str
            A static JWT token used for all requests.

        Returns
        -------
        AsyncAlbert
            A configured async client authenticated with the given token.
        """
        return cls(base_url=base_url, token=token)

    @classmethod
    def from_client_credentials(
        cls,
        *,
        base_url: str | None = None,
        client_id: str,
        client_secret: str,
    ) -> AsyncAlbert:
        """
        Create an AsyncAlbert client using client credentials authentication.

        Parameters
        ----------
        base_url : str | None, optional
            The base URL of the Albert API. Falls back to the ``ALBERT_BASE_URL``
            environment variable or "https://app.albertinvent.com".
        client_id : str
            The OAuth2 client ID.
        client_secret : str
            The OAuth2 client secret.

        Returns
        -------
        AsyncAlbert
            A configured async client that refreshes tokens automatically.
        """
        resolved_base_url = base_url or default_albert_base_url()
        creds = AlbertClientCredentials(
            id=client_id,
            secret=SecretStr(client_secret),
            base_url=resolved_base_url,
        )
        return cls(auth_manager=creds)

    @property
    def chat_sessions(self) -> ChatSessionCollection:
        return ChatSessionCollection(session=self.session)

    @property
    def chat_messages(self) -> ChatMessageCollection:
        return ChatMessageCollection(session=self.session)

    @property
    def chat_folders(self) -> ChatFolderCollection:
        return ChatFolderCollection(session=self.session)

    @property
    def chat_flags(self) -> ChatFlagCollection:
        return ChatFlagCollection(session=self.session)

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self.session.aclose()

    async def __aenter__(self) -> AsyncAlbert:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()
