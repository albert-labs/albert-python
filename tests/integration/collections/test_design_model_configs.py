import uuid
from contextlib import suppress

import pytest

from albert.client import Albert
from albert.exceptions import AlbertClientError, ConflictError, NotFoundError
from albert.resources.design_model_configs import (
    DesignModelConfig,
    DesignModelConfigApplyResponse,
    DesignModelConfigFeaturePreview,
    DesignModelConfigReferences,
    DesignModelConfigResolvedFeatures,
    DesignModelConfigState,
    DesignModelConfigValidationResponse,
    FeatureMask,
    OutputEntry,
    SetOutputOperation,
)
from albert.resources.design_operands import IngredientAmountOperand
from albert.resources.projects import Project
from albert.resources.smart_datasets import SmartDataset
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("datatemplates")

ignore_in_ten0 = pytest.mark.xfail(
    reason="The v4 design service is not enabled for the TEN0 test tenant.",
    strict=False,
)

builder_not_deployed = pytest.mark.xfail(
    reason="design-model-config service routes not yet deployed",
    strict=False,
)


def _create_config(client: Albert, parent_id: str, name_suffix: str) -> DesignModelConfig:
    return client.design_model_configs.create(
        name=f"TEST - {name_suffix} {uuid.uuid4()}",
        parent_id=parent_id,
        description="SDK integration test config.",
    )


@ignore_in_ten0
@builder_not_deployed
def test_create_empty_and_get_by_id(client: Albert, seeded_projects: list[Project]) -> None:
    """Test creating an empty draft and reading it back."""
    config = _create_config(client, seeded_projects[0].id, "model config")
    try:
        assert isinstance(config, DesignModelConfig)
        assert config.id is not None
        assert config.state == DesignModelConfigState.DRAFT
        assert config.parent_id == seeded_projects[0].id

        fetched = client.design_model_configs.get_by_id(id=config.id)
        assert fetched.id == config.id
        assert fetched.name == config.name
    finally:
        with suppress(NotFoundError):
            client.design_model_configs.delete(id=config.id)


@ignore_in_ten0
@builder_not_deployed
def test_get_all_lists_configs_of_the_project(
    client: Albert, seeded_projects: list[Project]
) -> None:
    """Test that the project listing contains created configs."""
    parent_id = seeded_projects[0].id
    configs = [
        _create_config(client, parent_id, "listable A"),
        _create_config(client, parent_id, "listable B"),
    ]
    created_ids = {c.id for c in configs}
    try:
        listed = poll_until(
            lambda: [
                c
                for c in client.design_model_configs.get_all(parent_id=parent_id, max_items=100)
                if c.id in created_ids
            ],
            predicate=lambda found: {c.id for c in found} == created_ids,
        )
        assert {c.id for c in listed} == created_ids
    finally:
        for config in configs:
            with suppress(NotFoundError):
                client.design_model_configs.delete(id=config.id)


@ignore_in_ten0
@builder_not_deployed
def test_update_renames_a_draft(client: Albert, seeded_projects: list[Project]) -> None:
    """Test updating the name and description of a draft."""
    config = _create_config(client, seeded_projects[0].id, "rename me")
    try:
        config.description = "SDK integration test config, revised."
        updated = client.design_model_configs.update(design_model_config=config)
        assert updated.description == "SDK integration test config, revised."

        updated.name = f"TEST - renamed {uuid.uuid4()}"
        renamed = client.design_model_configs.update(design_model_config=updated)
        assert renamed.name == updated.name
    finally:
        with suppress(NotFoundError):
            client.design_model_configs.delete(id=config.id)


@ignore_in_ten0
@builder_not_deployed
def test_delete_removes_the_config(client: Albert, seeded_projects: list[Project]) -> None:
    """Test that a deleted config is no longer readable."""
    config = _create_config(client, seeded_projects[0].id, "delete me")
    client.design_model_configs.delete(id=config.id)
    with pytest.raises(NotFoundError):
        client.design_model_configs.get_by_id(id=config.id)


@ignore_in_ten0
@builder_not_deployed
def test_fork_rejects_a_draft(client: Albert, seeded_projects: list[Project]) -> None:
    """Test that forking a draft conflicts; only published configs can be forked."""
    config = _create_config(client, seeded_projects[0].id, "fork source")
    try:
        with pytest.raises(ConflictError):
            client.design_model_configs.fork(id=config.id)
    finally:
        with suppress(NotFoundError):
            client.design_model_configs.delete(id=config.id)


@ignore_in_ten0
@builder_not_deployed
def test_create_from_smart_dataset(
    client: Albert, seeded_projects: list[Project], seeded_smart_dataset: SmartDataset
) -> None:
    """Test creating a draft derived from a smart dataset."""
    config = client.design_model_configs.create(
        name=f"TEST - derived {uuid.uuid4()}",
        parent_id=seeded_projects[0].id,
        smart_dataset_id=seeded_smart_dataset.id,
    )
    try:
        assert config.state == DesignModelConfigState.DRAFT
        assert config.derived_from_id == seeded_smart_dataset.id
    finally:
        with suppress(NotFoundError):
            client.design_model_configs.delete(id=config.id)


@ignore_in_ten0
@builder_not_deployed
def test_apply_sets_an_output_without_a_dataset(
    client: Albert, seeded_projects: list[Project]
) -> None:
    """Test applying a setOutput operation with a structural-only check."""
    config = _create_config(client, seeded_projects[0].id, "apply ops")
    try:
        result = client.design_model_configs.apply(
            id=config.id,
            operations=[
                SetOutputOperation(
                    key="TAR1",
                    value=OutputEntry(
                        data_type="numeric",
                        features=FeatureMask(exclude=[IngredientAmountOperand(ingredient="INV1")]),
                    ),
                )
            ],
            validate=True,
        )
        assert isinstance(result, DesignModelConfigApplyResponse)
        assert "TAR1" in (result.design_model_config.outputs or {})
        assert isinstance(result.warnings, list)
    finally:
        with suppress(NotFoundError):
            client.design_model_configs.delete(id=config.id)


@ignore_in_ten0
@builder_not_deployed
def test_apply_resolve_without_a_dataset_is_rejected(
    client: Albert, seeded_projects: list[Project]
) -> None:
    """Test that resolve needs a smart dataset."""
    config = _create_config(client, seeded_projects[0].id, "resolve needs data")
    try:
        with pytest.raises(AlbertClientError):
            client.design_model_configs.apply(
                id=config.id,
                operations=[
                    SetOutputOperation(key="TAR1", value=OutputEntry(data_type="numeric"))
                ],
                resolve=True,
            )
    finally:
        with suppress(NotFoundError):
            client.design_model_configs.delete(id=config.id)


@ignore_in_ten0
@builder_not_deployed
def test_check_compatibility_resolve_and_preview_against_a_dataset(
    client: Albert, seeded_projects: list[Project], seeded_smart_dataset: SmartDataset
) -> None:
    """Test the dataset-backed reads on a config derived from a smart dataset."""
    config = client.design_model_configs.create(
        name=f"TEST - dataset reads {uuid.uuid4()}",
        parent_id=seeded_projects[0].id,
        smart_dataset_id=seeded_smart_dataset.id,
    )
    try:
        check = client.design_model_configs.check_compatibility(
            id=config.id, smart_dataset_id=seeded_smart_dataset.id
        )
        assert isinstance(check, DesignModelConfigValidationResponse)
        assert isinstance(check.valid, bool)

        resolved = client.design_model_configs.get_resolved_features(
            id=config.id, smart_dataset_id=seeded_smart_dataset.id
        )
        assert isinstance(resolved, DesignModelConfigResolvedFeatures)

        preview = client.design_model_configs.get_feature_values(
            id=config.id, smart_dataset_id=seeded_smart_dataset.id
        )
        assert isinstance(preview, DesignModelConfigFeaturePreview)
    finally:
        with suppress(NotFoundError):
            client.design_model_configs.delete(id=config.id)


@ignore_in_ten0
@builder_not_deployed
def test_publish_then_fork(client: Albert, seeded_projects: list[Project]) -> None:
    """Test publishing a draft and forking the published config into a new draft."""
    config = _create_config(client, seeded_projects[0].id, "publish me")
    forked = None
    try:
        published = client.design_model_configs.publish(id=config.id)
        assert published.state == DesignModelConfigState.PUBLISHED

        forked = client.design_model_configs.fork(id=published.id)
        assert forked.state == DesignModelConfigState.DRAFT
        assert forked.forked_from_id == published.id
    finally:
        if forked is not None:
            with suppress(NotFoundError):
                client.design_model_configs.delete(id=forked.id)
        with suppress(NotFoundError):
            client.design_model_configs.delete(id=config.id)


@ignore_in_ten0
@builder_not_deployed
def test_get_references_returns_a_reference_set(
    client: Albert, seeded_projects: list[Project]
) -> None:
    """Test reading what references a component of a draft."""
    config = _create_config(client, seeded_projects[0].id, "references")
    try:
        references = client.design_model_configs.get_references(
            id=config.id, component="outputs/TAR1"
        )
        assert isinstance(references, DesignModelConfigReferences)
    finally:
        with suppress(NotFoundError):
            client.design_model_configs.delete(id=config.id)
