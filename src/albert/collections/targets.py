from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import ProjectId, TargetId
from albert.resources.targets import Target


class TargetCollection(BaseCollection):
    """Manage Targets in the Albert platform (🧪 Beta).

    A Target is a desired value or acceptable range for a measured property. It
    ties a data template and data column (the property being measured) to a
    target value constraint ([`Criterion`][albert.resources.targets.Criterion], e.g.
    "greater than or equal to 90" or "between 10 and 20"), optionally scoped to a
    project and to specific parameter conditions. Targets let you express the
    performance a formulation is aiming for and compare results against it.

    Targets are referenced by their Target ID (format ``TAR...``, e.g. ``"TAR1"``).

    This collection is accessed as ``client.targets``.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for target requests.

    Methods
    -------
    create(target) -> Target
        Create a new target.
    get_by_id(id, parent_id=None) -> Target
        Get a single target by its ID.
    get_by_ids(ids) -> list[Target]
        Get many targets by their IDs.
    delete(id) -> None
        Delete a target by its ID.

    Examples
    --------
    ```python
    from albert import Albert
    client = Albert()
    target = client.targets.get_by_id(id="TAR1")
    print(target.name, target.target_value)
    ```
    """

    _api_version = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a TargetCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{TargetCollection._api_version}/targets"

    def create(self, *, target: Target) -> Target:
        """Create a new target.

        Parameters
        ----------
        target : Target
            The target to create.

        Returns
        -------
        Target
            The newly created target, including its assigned Target ID.

        Examples
        --------
        ```python
        from albert.resources.targets import (
            Target,
            TargetType,
            Criterion,
            ComparisonOperator,
        )
        target = client.targets.create(
            target=Target(
                name="Viscosity spec",
                type=TargetType.PERFORMANCE,
                data_template_id="DAT1",
                data_column_id="DAC1",
                target_value=Criterion(operator=ComparisonOperator.GTE, value=90),
                is_required=True,
            )
        )
        ```
        """
        response = self.session.post(
            self.base_path,
            json=target.model_dump(by_alias=True, exclude_none=True, mode="json"),
        )
        return Target(**response.json())

    @validate_call
    def get_by_id(self, *, id: TargetId, parent_id: ProjectId | None = None) -> Target:
        """Get a single target by its ID.

        Parameters
        ----------
        id : TargetId
            The Target ID to retrieve (format ``TAR...``).
        parent_id : ProjectId, optional
            The ID of a parent project to inherit the ACL (access control) policy
            from when the caller does not own the target record. Supply this if a
            plain lookup is denied for permission reasons.

        Returns
        -------
        Target
            The fully populated target.

        Examples
        --------
        ```python
        target = client.targets.get_by_id(id="TAR1")
        ```
        """
        url = f"{self.base_path}/{id}"
        params = {"parentId": parent_id} if parent_id is not None else None
        response = self.session.get(url, params=params)
        return Target(**response.json())

    def get_by_ids(self, *, ids: list[TargetId]) -> list[Target]:
        """Get many targets by their IDs.

        Parameters
        ----------
        ids : list[TargetId]
            The Target IDs to retrieve.

        Returns
        -------
        list[Target]
            The matching targets. Targets not found are omitted.

        Examples
        --------
        ```python
        targets = client.targets.get_by_ids(ids=["TAR1", "TAR2"])
        ```
        """
        url = f"{self.base_path}/ids"
        response = self.session.get(url, params={"id": ids})
        data = response.json()
        return [Target(**item) for item in data.get("Items", [])]

    def delete(self, *, id: TargetId) -> None:
        """Delete a target by its ID.

        Parameters
        ----------
        id : TargetId
            The Target ID to delete.

        Returns
        -------
        None

        Examples
        --------
        ```python
        client.targets.delete(id="TAR1")
        ```
        """
        url = f"{self.base_path}/{id}"
        self.session.delete(url)
