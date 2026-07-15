from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import ProjectId, SmartDatasetId, TargetId
from albert.core.shared.models.base import BaseSessionResource
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.resources.smart_datasets import SmartDatasetScope
from albert.resources.targets import Target

_PROJECTS_BASE_PATH = "/api/v3/projects"


class SmartProjectScope(BaseAlbertModel):
    """Scope of a smart project, defining which targets drive its smart dataset.

    Attributes
    ----------
    targets : list[TargetId]
        The target IDs that are part of this smart project scope.
    """

    targets: list[TargetId] = Field(default_factory=list, alias="targetIds")


class SmartProjectPatchAttribute(str, Enum):
    """Attributes supported when updating a smart project."""

    SMART_PROJECT = "smartproject"
    TARGETS = "targets"
    DATASET_ID = "datasetId"


class SmartProject(BaseSessionResource):
    """Smart project interface for a project.

    Attributes
    ----------
    project_id : ProjectId
        The ID of the project this smart project belongs to.
    scope : SmartProjectScope
        The target scope of the smart project.
    dataset_id : SmartDatasetId | None
        The ID of the smart dataset attached to the project, if any.
    logs : dict[str, Any] | None
        Build logs for the smart dataset.
    last_refresh_at : datetime | None
        When the smart dataset was last refreshed.

    Methods
    -------
    add_target(target) -> SmartProject
        Add a target to this smart project's scope.
    remove_target(target, delete) -> SmartProject
        Remove a target from this smart project's scope.
    update_dataset(dataset) -> SmartProject
        Update the smart dataset attached to this smart project.
    """

    project_id: ProjectId
    scope: SmartProjectScope
    dataset_id: SmartDatasetId | None = Field(default=None, alias="datasetId")
    logs: dict[str, Any] | None = None
    last_refresh_at: datetime | None = Field(default=None, alias="lastRefreshAt")

    def _refresh(self) -> SmartProject:
        """Re-fetch the smart project and update this instance in place."""
        response = self.session.get(f"{_PROJECTS_BASE_PATH}/{self.project_id}/getSmartProject")
        smart = response.json().get("smart", [])
        if smart:
            refreshed = SmartProject(**smart[0], session=self.session, project_id=self.project_id)
            self.scope = refreshed.scope
            self.dataset_id = refreshed.dataset_id
            self.logs = refreshed.logs
            self.last_refresh_at = refreshed.last_refresh_at
        return self

    def _update(self, *, data: list[PatchDatum]) -> SmartProject:
        """Update this smart project in place.

        Parameters
        ----------
        data : list[PatchDatum]
            The smart project attributes to update.

        Returns
        -------
        SmartProject
            This smart project, updated.
        """
        payload = PatchPayload(data=data)
        _ = self.session.patch(
            f"{_PROJECTS_BASE_PATH}/{self.project_id}/smart",
            json=payload.model_dump(mode="json", by_alias=True),
        )
        return self._refresh()

    def add_target(self, *, target: Target | TargetId) -> SmartProject:
        """Add a target to this smart project's scope.

        Parameters
        ----------
        target : Target | TargetId
            The target to add. An existing target, a ``TargetId`` or a ``Target``
            with an ``id``, is registered to the scope. A new ``Target`` (without
            an ``id``) is created and registered.

        Returns
        -------
        SmartProject
            This smart project, updated.
        """

        # If the target is a new target, create it and add it to the scope.
        if isinstance(target, Target) and target.id is None:
            self.session.post(
                f"{_PROJECTS_BASE_PATH}/{self.project_id}/addTargetToProject",
                json=target.model_dump(by_alias=True, exclude_none=True, mode="json"),
            )
            return self._refresh()

        # If the target is an existing target, add it to the scope.
        target_id = target.id if isinstance(target, Target) else target
        return self._update(
            data=[
                PatchDatum(
                    operation=PatchOperation.ADD,
                    attribute=SmartProjectPatchAttribute.TARGETS,
                    new_value=[target_id],
                )
            ]
        )

    def remove_target(self, *, target: Target | TargetId, delete: bool = False) -> SmartProject:
        """Remove a target from this smart project's scope.

        Parameters
        ----------
        target : Target | TargetId
            The target to remove, or its ID.
        delete : bool, optional
            When ``True``, also deactivate the target record. When ``False``,
            only remove the target from the scope.

        Returns
        -------
        SmartProject
            This smart project, updated.
        """
        target_id = target.id if isinstance(target, Target) else target
        self.session.delete(
            f"{_PROJECTS_BASE_PATH}/{self.project_id}/deleteTarget/{target_id}",
            params={"delete": delete},
        )
        return self._refresh()

    def update_dataset(
        self,
        *,
        dataset: SmartDatasetId | SmartDatasetScope | None = None,
    ) -> SmartProject:
        """Update the smart dataset attached to this smart project.

        Parameters
        ----------
        dataset : SmartDatasetId | SmartDatasetScope | None, optional
            If a SmartDatasetId, that existing smart dataset is attached to the smart project.
            If a SmartDatasetScope, a new smart dataset is built from the scope and attached to the smart project.
            If None, the current smart project scope is used to build a new smart dataset.

        Returns
        -------
        SmartProject
            This smart project, updated.
        """

        # Existing dataset ID (SmartDatasetId is an Annotated[str, ...] alias, so check str)
        # -> attach that dataset to the smart record.
        if isinstance(dataset, str):
            return self._update(
                data=[
                    PatchDatum(
                        operation=PatchOperation.UPDATE,
                        attribute=SmartProjectPatchAttribute.DATASET_ID,
                        new_value=dataset,
                    )
                ]
            )

        # Otherwise build a new dataset: from the given scope, or from the current scope when None.
        if isinstance(dataset, SmartDatasetScope):
            scope = dataset
        else:
            scope = SmartDatasetScope(
                project_ids=[self.project_id],
                target_ids=self.scope.targets,
                sheet_ids=None,
                target_parent_ids={t: self.project_id for t in self.scope.targets},
            )

        _ = self.session.post(
            f"{_PROJECTS_BASE_PATH}/{self.project_id}/addDatasetToProject",
            json={"scope": scope.model_dump(by_alias=True, exclude_none=False, mode="json")},
        )
        return self._refresh()
