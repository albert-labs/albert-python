from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.resources.localizations import Localization, LocalizationPatchDatum


class LocalizationCollection(BaseCollection):
    """Manage Localizations in the Albert platform.

    A Localization holds the translations of an entity's localizable fields
    (name, description, enum option text) into other languages. Reading the
    localizations of an entity (e.g. a data template) returns one
    [`Localization`][albert.resources.localizations.Localization] for the entity
    itself plus one per localizable child record (data columns, parameters),
    each identified by its ``unique_id``.

    This collection is accessed as ``client.localizations``.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        rows = client.localizations.get_by_id(id="DAT1")
        for row in rows:
            print(row.unique_id, row.localization)
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for localization requests.

    Methods
    -------
    get_by_id(id) -> list[Localization]
        Get all localizations for an entity by its ID.
    update(id, patches) -> None
        Set translations on an entity or its child records.
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a LocalizationCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{LocalizationCollection._api_version}/localizations"

    @validate_call
    def get_by_id(self, *, id: str) -> list[Localization]:
        """Get all localizations for an entity by its ID.

        Returns the entity's own translations plus the translations of its
        localizable child records.

        !!! example
            ```python
            rows = client.localizations.get_by_id(id="DAT1")
            rows[0].localization
            # {'name': {'de': 'Datenvorlage'}}
            ```

        Parameters
        ----------
        id : str
            The Albert ID of the entity (e.g. ``"DAT1"``).

        Returns
        -------
        list[Localization]
            The localization rows for the entity and its child records.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return [Localization(**item) for item in response.json().get("items", [])]

    @validate_call
    def update(self, *, id: str, patches: list[LocalizationPatchDatum]) -> None:
        """Set translations on an entity or its child records.

        Each patch targets one attribute of one record (via ``unique_id``) in one
        language, with ``operation="add"`` to create a translation,
        ``operation="update"`` to change an existing one, and
        ``operation="delete"`` to remove one.

        !!! example
            ```python
            from albert.resources.localizations import (
                LocalizationLanguage,
                LocalizationPatchDatum,
            )

            client.localizations.update(
                id="DAT1",
                patches=[
                    LocalizationPatchDatum(
                        operation="add",
                        attribute="name",
                        language=LocalizationLanguage.GERMAN,
                        unique_id="DAT",
                        new_value="Datenvorlage",
                    )
                ],
            )
            ```

        Parameters
        ----------
        id : str
            The Albert ID of the entity (e.g. ``"DAT1"``).
        patches : list[LocalizationPatchDatum]
            The translation changes to apply.

        Returns
        -------
        None

        Notes
        -----
        An empty ``patches`` list is a no-op.

        Each patch entry targets a single translation via ``attribute`` (e.g.
        ``"name"``), ``language``, and ``unique_id``. ``operation="add"`` takes only
        ``new_value``; ``operation="update"`` takes ``old_value`` and ``new_value``;
        ``operation="delete"`` takes only ``old_value``.
        """
        if not patches:
            return
        self.session.patch(
            f"{self.base_path}/{id}",
            json={
                "data": [
                    patch.model_dump(by_alias=True, exclude_unset=True, mode="json")
                    for patch in patches
                ]
            },
        )
