from collections.abc import Iterator

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.design_spaces import _LastKeyCursorPaginator
from albert.core.pagination import PaginationMode
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import DesignModelConfigId, ProjectId, SmartDatasetId
from albert.resources.design_model_configs import (
    CreateDesignModelConfigRequest,
    DesignModelConfig,
    DesignModelConfigApplyResponse,
    DesignModelConfigCreated,
    DesignModelConfigFeaturePreview,
    DesignModelConfigForkRequest,
    DesignModelConfigOperation,
    DesignModelConfigOperationsRequest,
    DesignModelConfigPreviewRequest,
    DesignModelConfigReferences,
    DesignModelConfigResolvedFeatures,
    DesignModelConfigState,
    DesignModelConfigValidationRequest,
    DesignModelConfigValidationResponse,
)


class DesignModelConfigCollection(BaseCollection):
    """Manage Design Model Configs in the Albert platform (🧪 Beta).

    A design model config says how a design run models a smart dataset: which targets
    to predict (its outputs), how to transform each one, and which of the default
    features each one uses.

    A config is created as a draft, edited with builder operations, checked against a
    smart dataset, and published. A published config is frozen; editing one means
    forking it into a new draft. Publishing validates and freezes; it trains nothing.

    This collection is accessed as ``client.design_model_configs``.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        config = client.design_model_configs.create(
            name="Clearcoat surrogate",
            parent_id="PRO123",
            smart_dataset_id="SDT123",
        )
        config.state
        # <DesignModelConfigState.DRAFT: 'draft'>
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for design-model-config requests.

    Methods
    -------
    create(name, parent_id, description=None, smart_dataset_id=None) -> DesignModelConfigCreated
        Create a draft design model config, empty or derived from a smart dataset.
    get_by_id(id) -> DesignModelConfig
        Get a single design model config by its ID.
    get_all(parent_id, state=None, max_items=None) -> Iterator[DesignModelConfig]
        Get all design model configs in a project.
    update(design_model_config) -> DesignModelConfig
        Update the name or description of a draft design model config.
    apply(id, operations, validate=False, resolve=False, preview_rows=None, dry_run=False, smart_dataset_id=None) -> DesignModelConfigApplyResponse
        Apply builder operations to a draft design model config.
    check_compatibility(id, smart_dataset_id) -> DesignModelConfigValidationResponse
        Check a design model config against a smart dataset.
    get_resolved_features(id, smart_dataset_id) -> DesignModelConfigResolvedFeatures
        Get the features a config resolves to against a smart dataset.
    get_feature_values(id, smart_dataset_id) -> DesignModelConfigFeaturePreview
        Preview a few dataset rows run through the config's features.
    publish(id) -> DesignModelConfig
        Publish a draft design model config, freezing it.
    fork(id, parent_id=None) -> DesignModelConfig
        Fork a published design model config into a new editable draft.
    get_references(id, component) -> DesignModelConfigReferences
        Get what references a component of a design model config.
    delete(id) -> None
        Delete a design model config by its ID.
    """

    _api_version = "v4"
    _updatable_attributes = {"name", "description"}
    _non_deletable_attributes = {"name"}

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{DesignModelConfigCollection._api_version}/design/model-configs"

    @validate_call
    def create(
        self,
        *,
        name: str,
        parent_id: ProjectId,
        description: str | None = None,
        smart_dataset_id: SmartDatasetId | None = None,
    ) -> DesignModelConfigCreated:
        """Create a draft design model config.

        Pass ``smart_dataset_id`` to derive the draft from a smart dataset: one bare
        output per target, with no feature masks. Omit it to start empty and add outputs
        with
        [`apply`][albert.collections.design_model_configs.DesignModelConfigCollection.apply].

        !!! example
            ```python
            config = client.design_model_configs.create(
                name="Clearcoat surrogate",
                parent_id="PRO123",
                description="Feature choices for the 2027 EU clearcoat line.",
                smart_dataset_id="SDT123",
            )
            ```

        Parameters
        ----------
        name : str
            Display name of the config.
        parent_id : ProjectId
            The project (format ``PRO...``) that owns the config and controls access to it.
        description : str, optional
            Free-text description of the config's intent.
        smart_dataset_id : SmartDatasetId, optional
            Smart dataset (format ``SDT...``) to derive the first draft from. Omit for an
            empty draft.

        Returns
        -------
        DesignModelConfigCreated
            The created draft design model config, with any ``warnings``.
        """
        body = CreateDesignModelConfigRequest(
            name=name,
            parent_id=parent_id,
            description=description,
            smart_dataset_id=smart_dataset_id,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(self.base_path, json=body)
        return DesignModelConfigCreated(**response.json())

    @validate_call
    def get_by_id(self, *, id: DesignModelConfigId) -> DesignModelConfig:
        """Get a single design model config by its ID.

        !!! example
            ```python
            config = client.design_model_configs.get_by_id(id="DMC123")
            config.name
            # 'Clearcoat surrogate'
            ```

        Parameters
        ----------
        id : DesignModelConfigId
            The design model config ID (format ``DMC...``).

        Returns
        -------
        DesignModelConfig
            The fully populated design model config.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return DesignModelConfig(**response.json())

    @validate_call
    def get_all(
        self,
        *,
        parent_id: ProjectId,
        state: DesignModelConfigState | None = None,
        max_items: int | None = None,
    ) -> Iterator[DesignModelConfig]:
        """Get all design model configs in a project.

        Results are returned as a lazily paginated iterator.

        !!! example
            ```python
            for config in client.design_model_configs.get_all(parent_id="PRO123"):
                print(config.id, config.name, config.state)
            ```

        Parameters
        ----------
        parent_id : ProjectId
            The project (format ``PRO...``) whose configs to list.
        state : DesignModelConfigState, optional
            Limit to drafts or to published configs.
        max_items : int, optional
            Stop after this many configs.

        Returns
        -------
        Iterator[DesignModelConfig]
            A lazily paginated iterator over the project's design model configs.
        """
        params = {"parentId": parent_id}
        if state is not None:
            params["state"] = state
        return _LastKeyCursorPaginator(
            mode=PaginationMode.KEY,
            path=self.base_path,
            session=self.session,
            params=params,
            max_items=max_items,
            deserialize=lambda items: [DesignModelConfig(**item) for item in items],
        )

    @validate_call
    def update(self, *, design_model_config: DesignModelConfig) -> DesignModelConfig:
        """Update the name or description of a draft design model config.

        Retrieve the config with
        [`get_by_id`][albert.collections.design_model_configs.DesignModelConfigCollection.get_by_id],
        modify ``name`` and/or ``description``, then pass it here. Only changed fields
        are applied. Outputs are edited with
        [`apply`][albert.collections.design_model_configs.DesignModelConfigCollection.apply].

        A published config is frozen and cannot be updated;
        [`fork`][albert.collections.design_model_configs.DesignModelConfigCollection.fork]
        it into a new draft instead.

        !!! example
            ```python
            config = client.design_model_configs.get_by_id(id="DMC123")
            config.description = "Feature choices for the 2027 EU clearcoat line, rev B"
            updated = client.design_model_configs.update(design_model_config=config)
            ```

        Parameters
        ----------
        design_model_config : DesignModelConfig
            The config carrying the desired changes. Its ``id`` identifies which config
            to update.

        Returns
        -------
        DesignModelConfig
            The updated design model config.

        Notes
        -----
        The following fields can be updated: ``name``, ``description``.
        """
        existing = self.get_by_id(id=design_model_config.id)
        patch_payload = self._generate_patch_payload(
            existing=existing, updated=design_model_config
        ).model_dump(mode="json", by_alias=True)
        if not patch_payload["data"]:
            return existing
        response = self.session.patch(
            f"{self.base_path}/{design_model_config.id}", json=patch_payload
        )
        return DesignModelConfig(**response.json())

    @validate_call
    def apply(
        self,
        *,
        id: DesignModelConfigId,
        operations: list[DesignModelConfigOperation],
        validate: bool = False,
        resolve: bool = False,
        preview_rows: int | None = None,
        dry_run: bool = False,
        smart_dataset_id: SmartDatasetId | None = None,
    ) -> DesignModelConfigApplyResponse:
        """Apply builder operations to a draft design model config.

        Operations apply atomically and in the order given: if any one cannot apply,
        nothing is applied and the call fails with the violations listed. The three
        operations:

        - [`SetOutputOperation`][albert.resources.design_model_configs.SetOutputOperation]:
          upsert one target's whole wiring (data type, transform and feature mask).
        - [`RemoveComponentOperation`][albert.resources.design_spaces.RemoveComponentOperation]:
          remove an output by its path, ``outputs/<target id>``.
        - [`UpdateComponentOperation`][albert.resources.design_spaces.UpdateComponentOperation]:
          change one field of an output in place (for example ``outputTransform``).

        A transform other than ``none`` on a categorical output is rejected
        (``invalid_settings``), and fields that are not yet available are rejected
        (``invalid_constraint``).

        ``resolve`` and ``preview_rows`` need ``smart_dataset_id`` (the call fails
        otherwise). With ``validate``, a dataset adds the dataset checks to the
        structural ones; without one, ``validate`` runs the structural checks only.

        !!! example
            ```python
            from albert.resources.design_model_configs import (
                FeatureMask,
                OutputEntry,
                SetOutputOperation,
            )
            from albert.resources.design_operands import IngredientAmountOperand

            result = client.design_model_configs.apply(
                id="DMC123",
                operations=[
                    SetOutputOperation(
                        key="TAR046",
                        value=OutputEntry(
                            data_type="numeric",
                            features=FeatureMask(
                                exclude=[IngredientAmountOperand(ingredient="INV009")]
                            ),
                        ),
                    )
                ],
                validate=True,
                resolve=True,
                smart_dataset_id="SDT123",
            )
            result.validation.valid
            # True
            ```

        Parameters
        ----------
        id : DesignModelConfigId
            The design model config ID (format ``DMC...``).
        operations : list[DesignModelConfigOperation]
            The operations to apply, in order.
        validate : bool, optional
            Fold a check into the result. An invalid outcome is a normal result with
            ``validation.valid == False``, not an exception.
        resolve : bool, optional
            Fold the resolved features into the result. Needs ``smart_dataset_id``.
        preview_rows : int, optional
            Fold a feature preview of this many dataset rows into the result. The
            server clamps it to 1..25. Needs ``smart_dataset_id``.
        dry_run : bool, optional
            Compute the would-be result without saving it.
        smart_dataset_id : SmartDatasetId, optional
            Smart dataset (format ``SDT...``) for ``resolve``, ``preview_rows`` and the
            dataset checks of ``validate``.

        Returns
        -------
        DesignModelConfigApplyResponse
            The resulting design model config (``design_model_config``), any non-blocking
            findings, and the validation, resolved features and preview when asked for.

        Raises
        ------
        AlbertClientError
            An operation could not apply (the violations are listed), ``resolve`` or
            ``preview_rows`` was given without ``smart_dataset_id``, or the config is
            published.
        AlbertHTTPError
            Other failures.
        """
        body = DesignModelConfigOperationsRequest(
            operations=operations,
            validate_=validate,
            resolve=resolve,
            preview=(
                DesignModelConfigPreviewRequest(num_rows=preview_rows)
                if preview_rows is not None
                else None
            ),
            dry_run=dry_run,
            smart_dataset_id=smart_dataset_id,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(f"{self.base_path}/{id}/operations", json=body)
        return DesignModelConfigApplyResponse(**response.json())

    @validate_call
    def check_compatibility(
        self, *, id: DesignModelConfigId, smart_dataset_id: SmartDatasetId
    ) -> DesignModelConfigValidationResponse:
        """Check a design model config against a smart dataset.

        ``valid=False`` with populated ``violations`` is a normal result, not an
        exception.

        !!! example
            ```python
            result = client.design_model_configs.check_compatibility(
                id="DMC123", smart_dataset_id="SDT123"
            )
            if not result.valid:
                for violation in result.violations:
                    print(violation.code, violation.message)
            ```

        Parameters
        ----------
        id : DesignModelConfigId
            The design model config ID (format ``DMC...``).
        smart_dataset_id : SmartDatasetId
            Smart dataset (format ``SDT...``) to check the config against.

        Returns
        -------
        DesignModelConfigValidationResponse
            The result with ``valid`` and ``violations``.
        """
        body = DesignModelConfigValidationRequest(smart_dataset_id=smart_dataset_id).model_dump(
            by_alias=True, mode="json"
        )
        response = self.session.post(
            f"{self.base_path}/{id}/validation", json=body, retry_safe=True
        )
        return DesignModelConfigValidationResponse(**response.json())

    @validate_call
    def get_resolved_features(
        self, *, id: DesignModelConfigId, smart_dataset_id: SmartDatasetId
    ) -> DesignModelConfigResolvedFeatures:
        """Get the features a config resolves to against a smart dataset.

        Returns every concrete feature (with a stable ``key``, its family and the
        quantity it computes) and, per output, the keys of the features that output's
        mask routes.

        !!! example
            ```python
            resolved = client.design_model_configs.get_resolved_features(
                id="DMC123", smart_dataset_id="SDT123"
            )
            resolved.outputs["TAR046"]
            # ['ingredient/INV001', 'parameter/DAT1#PRM1#UNI1']
            ```

        Parameters
        ----------
        id : DesignModelConfigId
            The design model config ID (format ``DMC...``).
        smart_dataset_id : SmartDatasetId
            Smart dataset (format ``SDT...``) to resolve against.

        Returns
        -------
        DesignModelConfigResolvedFeatures
            The resolved feature set, per-output routing and warnings.
        """
        response = self.session.get(
            f"{self.base_path}/{id}/features", params={"smartDatasetId": smart_dataset_id}
        )
        return DesignModelConfigResolvedFeatures(**response.json())

    @validate_call
    def get_feature_values(
        self, *, id: DesignModelConfigId, smart_dataset_id: SmartDatasetId
    ) -> DesignModelConfigFeaturePreview:
        """Preview a few dataset rows run through the config's features.

        The first rows of the dataset are featurized with the config's resolved features;
        no model is fit. Feature values are limited to the first keyed feature columns
        (``columns_truncated`` says when), while ``summary`` covers every keyed feature.
        Features without a stable key (for example molecular descriptors) are always
        used and are reported under ``automatic_features``, not as values.

        !!! example
            ```python
            preview = client.design_model_configs.get_feature_values(
                id="DMC123", smart_dataset_id="SDT123"
            )
            preview.rows[0].values
            ```

        Parameters
        ----------
        id : DesignModelConfigId
            The design model config ID (format ``DMC...``).
        smart_dataset_id : SmartDatasetId
            Smart dataset (format ``SDT...``) to featurize rows from.

        Returns
        -------
        DesignModelConfigFeaturePreview
            The previewed rows, per-feature summary and automatic features.
        """
        response = self.session.get(
            f"{self.base_path}/{id}/feature-values", params={"smartDatasetId": smart_dataset_id}
        )
        return DesignModelConfigFeaturePreview(**response.json())

    @validate_call
    def publish(self, *, id: DesignModelConfigId) -> DesignModelConfig:
        """Publish a draft design model config, freezing it.

        The config is validated first, without a dataset: one with blocking violations
        cannot be published, and an already-published config conflicts. Publishing trains
        nothing. Published configs are immutable; to change one,
        [`fork`][albert.collections.design_model_configs.DesignModelConfigCollection.fork]
        it into a new draft.

        !!! example
            ```python
            published = client.design_model_configs.publish(id="DMC123")
            published.state
            # <DesignModelConfigState.PUBLISHED: 'published'>
            ```

        Parameters
        ----------
        id : DesignModelConfigId
            The design model config ID (format ``DMC...``).

        Returns
        -------
        DesignModelConfig
            The published design model config.

        Raises
        ------
        AlbertClientError
            The config has blocking violations (they are listed) or is already published.
        AlbertHTTPError
            Other failures.
        """
        response = self.session.post(f"{self.base_path}/{id}/publication")
        return DesignModelConfig(**response.json())

    @validate_call
    def fork(
        self, *, id: DesignModelConfigId, parent_id: ProjectId | None = None
    ) -> DesignModelConfig:
        """Fork a published design model config into a new editable draft.

        The new draft remembers which published config it came from
        (``forked_from_id``). Forking a draft conflicts; only published configs can be
        forked.

        !!! example
            ```python
            draft = client.design_model_configs.fork(id="DMC123")
            draft.state
            # <DesignModelConfigState.DRAFT: 'draft'>
            ```

        Parameters
        ----------
        id : DesignModelConfigId
            The published design model config ID (format ``DMC...``).
        parent_id : ProjectId, optional
            Target project (format ``PRO...``) for the fork. Omit to keep the source's
            project.

        Returns
        -------
        DesignModelConfig
            The new draft design model config.
        """
        body = DesignModelConfigForkRequest(parent_id=parent_id).model_dump(
            by_alias=True, mode="json", exclude_none=True
        )
        response = self.session.post(f"{self.base_path}/{id}/forks", json=body)
        return DesignModelConfig(**response.json())

    @validate_call
    def get_references(
        self, *, id: DesignModelConfigId, component: str
    ) -> DesignModelConfigReferences:
        """Get what references a component of a design model config.

        Powers safe removal: check whether anything still points at the component
        before removing it with
        [`apply`][albert.collections.design_model_configs.DesignModelConfigCollection.apply].

        !!! example
            ```python
            refs = client.design_model_configs.get_references(
                id="DMC123", component="outputs/TAR046"
            )
            ```

        Parameters
        ----------
        id : DesignModelConfigId
            The design model config ID (format ``DMC...``).
        component : str
            Component path, ``<collection>/<key>`` (e.g. ``"outputs/TAR046"``).

        Returns
        -------
        DesignModelConfigReferences
            The references to the component.
        """
        response = self.session.get(
            f"{self.base_path}/{id}/references", params={"component": component}
        )
        return DesignModelConfigReferences(**response.json())

    @validate_call
    def delete(self, *, id: DesignModelConfigId) -> None:
        """Delete a design model config by its ID.

        A published config that a design run still references cannot be deleted.

        !!! example
            ```python
            client.design_model_configs.delete(id="DMC123")
            ```

        Parameters
        ----------
        id : DesignModelConfigId
            The design model config ID (format ``DMC...``).

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")
