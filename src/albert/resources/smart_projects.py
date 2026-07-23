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
    """Scope of a smart project, defining which targets drive its smart dataset."""

    targets: list[TargetId] = Field(default_factory=list, alias="targetIds")
    """The target IDs that are part of this smart project scope."""


class SmartProjectPatchAttribute(str, Enum):
    """Attributes supported when updating a smart project."""

    SMART_PROJECT = "smartproject"
    TARGETS = "targets"
    DATASET_ID = "datasetId"


class SmartProject(BaseSessionResource):
    """Project-bound interface for Smart Projects workflows.

    [`SmartProject`][albert.resources.smart_projects.SmartProject] is the SDK
    entry point for anything that mirrors the Smart Projects product experience:
    targets and smart datasets scoped to a specific project. Access it via
    [`Project.smart`][albert.resources.projects.Project.smart] after fetching or
    creating a project.

    For resources that exist independently of a project, use the standalone
    collections instead:
    [`TargetCollection`][albert.collections.targets.TargetCollection]
    (``client.targets``) and
    [`SmartDatasetCollection`][albert.collections.smart_datasets.SmartDatasetCollection]
    (``client.smart_datasets``). Those collections create entities on their own;
    associating them with a project requires separate steps.

    Methods on this resource that accept new entity payloads (without an existing
    ID) perform create-and-assign in a single call. No prior call to
    ``client.targets.create`` or ``client.smart_datasets.create`` is required
    for the project-bound Smart Projects flow.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.targets import (
            Target,
            TargetType,
            Criterion,
            ComparisonOperator,
        )

        client = Albert()
        project = client.projects.get_by_id(id="PRO123")
        smart = project.smart

        # Create a target and add it to the project in one step
        smart.add_target(
            target=Target(
                name="Viscosity spec",
                type=TargetType.PERFORMANCE,
                data_template_id="DAT1",
                data_column_id="DAC1",
                target_value=Criterion(operator=ComparisonOperator.GTE, value=90),
            )
        )

        # Build and attach a smart dataset from the current target scope
        smart.update_dataset()
        ```

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
    """The ID of the project this smart project belongs to."""

    scope: SmartProjectScope
    """The target scope of the smart project."""

    dataset_id: SmartDatasetId | None = Field(default=None, alias="datasetId")
    """The ID of the smart dataset attached to the project, if any."""

    logs: dict[str, Any] | None = None
    """Build logs for the smart dataset."""

    last_refresh_at: datetime | None = Field(default=None, alias="lastRefreshAt")
    """When the smart dataset was last refreshed."""

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

        When adding a target as part of a Smart Projects workflow, pass a new
        [`Target`][albert.resources.targets.Target] without an ``id``. That
        creates the target and associates it with this project in one call; no
        separate ``client.targets.create`` is needed.

        Parameters
        ----------
        target : Target | TargetId
            The target to add. See Notes for how the argument is interpreted.

        Returns
        -------
        SmartProject
            This smart project, updated.

        Notes
        -----
        ``target`` is interpreted in three ways:

        * A [`Target`][albert.resources.targets.Target] **without** an ``id``:
          create the target and associate it with this project. This is the
          Smart Projects UX path.
        * A [`Target`][albert.resources.targets.Target] **with** an ``id``:
          associate that existing target with this project (does not create a
          new target).
        * A [`TargetId`][albert.core.shared.identifiers.TargetId]: associate
          that existing target with this project.

        Only the first path (new ``Target`` without ``id``) is supported by the
        current Smart Projects product UI. The other paths are available
        programmatically.
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

        When building a dataset as part of a Smart Projects workflow, pass a
        [`SmartDatasetScope`][albert.resources.smart_datasets.SmartDatasetScope]
        or omit ``dataset`` entirely. Either choice builds a new smart dataset
        from the scope and attaches it to this project in one call; no separate
        ``client.smart_datasets.create`` is needed.

        Parameters
        ----------
        dataset : SmartDatasetId | SmartDatasetScope | None, optional
            If a [`SmartDatasetId`][albert.core.shared.identifiers.SmartDatasetId],
            attach that existing smart dataset to this project. If a
            [`SmartDatasetScope`][albert.resources.smart_datasets.SmartDatasetScope],
            build a new smart dataset from the scope and attach it. If ``None``,
            build from this smart project's current target scope.

        Returns
        -------
        SmartProject
            This smart project, updated.

        Notes
        -----
        When ``dataset`` is a
        [`SmartDatasetScope`][albert.resources.smart_datasets.SmartDatasetScope]
        or ``None``, this method performs create-and-assign in one step for the
        project-bound Smart Projects flow. When ``dataset`` is a
        [`SmartDatasetId`][albert.core.shared.identifiers.SmartDatasetId], an
        existing smart dataset built via
        [`SmartDatasetCollection`][albert.collections.smart_datasets.SmartDatasetCollection]
        is attached instead.
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
