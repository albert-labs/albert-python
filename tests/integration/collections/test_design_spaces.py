import uuid
from contextlib import suppress

import pytest

from albert.client import Albert
from albert.exceptions import ConflictError, NotFoundError
from albert.resources.design_spaces import (
    DesignSpace,
    DesignSpaceApplyResponse,
    DesignSpaceReferences,
    DesignSpaceSample,
    DesignSpaceState,
    DesignSpaceValidationResponse,
    IngredientEntry,
    SetIngredientOperation,
)
from albert.resources.projects import Project
from albert.resources.smart_datasets import SmartDataset
from tests.utils.wait import poll_until

pytestmark = pytest.mark.xdist_group("datatemplates")

ignore_in_ten0 = pytest.mark.xfail(
    reason="The v4 design service is not enabled for the TEN0 test tenant.",
    strict=False,
)

builder_not_deployed = pytest.mark.xfail(
    reason="design-space builder not yet deployed",
    strict=False,
)


def _create_space(client: Albert, parent_id: str, name_suffix: str) -> DesignSpace:
    return client.design_spaces.create(
        name=f"TEST - {name_suffix} {uuid.uuid4()}",
        parent_id=parent_id,
        description="SDK integration test space.",
    )


@ignore_in_ten0
def test_create_empty_and_get_by_id(client: Albert, seeded_projects: list[Project]) -> None:
    """Test creating an empty draft and reading it back."""
    space = _create_space(client, seeded_projects[0].id, "design space")
    try:
        assert isinstance(space, DesignSpace)
        assert space.id is not None
        assert space.state == DesignSpaceState.DRAFT
        assert space.parent_id == seeded_projects[0].id

        fetched = client.design_spaces.get_by_id(id=space.id)
        assert fetched.id == space.id
        assert fetched.name == space.name
    finally:
        with suppress(NotFoundError):
            client.design_spaces.delete(id=space.id)


@ignore_in_ten0
def test_get_all_lists_spaces_of_the_project(
    client: Albert, seeded_projects: list[Project]
) -> None:
    """Test that the project listing contains created spaces."""
    parent_id = seeded_projects[0].id
    spaces = [
        _create_space(client, parent_id, "listable A"),
        _create_space(client, parent_id, "listable B"),
    ]
    created_ids = {s.id for s in spaces}
    try:
        listed = poll_until(
            lambda: [
                s
                for s in client.design_spaces.get_all(parent_id=parent_id, max_items=100)
                if s.id in created_ids
            ],
            predicate=lambda found: {s.id for s in found} == created_ids,
        )
        assert {s.id for s in listed} == created_ids
    finally:
        for space in spaces:
            with suppress(NotFoundError):
                client.design_spaces.delete(id=space.id)


@ignore_in_ten0
def test_update_renames_a_draft(client: Albert, seeded_projects: list[Project]) -> None:
    """Test updating the name and description of a draft."""
    space = _create_space(client, seeded_projects[0].id, "rename me")
    try:
        space.description = "SDK integration test space, revised."
        updated = client.design_spaces.update(design_space=space)
        assert updated.description == "SDK integration test space, revised."

        updated.name = f"TEST - renamed {uuid.uuid4()}"
        renamed = client.design_spaces.update(design_space=updated)
        assert renamed.name == updated.name
    finally:
        with suppress(NotFoundError):
            client.design_spaces.delete(id=space.id)


@ignore_in_ten0
def test_delete_removes_the_space(client: Albert, seeded_projects: list[Project]) -> None:
    """Test that a deleted space is no longer readable."""
    space = _create_space(client, seeded_projects[0].id, "delete me")
    client.design_spaces.delete(id=space.id)
    with pytest.raises(NotFoundError):
        client.design_spaces.get_by_id(id=space.id)


@ignore_in_ten0
def test_fork_rejects_a_draft(client: Albert, seeded_projects: list[Project]) -> None:
    """Test that forking a draft conflicts; only published spaces can be forked."""
    space = _create_space(client, seeded_projects[0].id, "fork source")
    try:
        with pytest.raises(ConflictError):
            client.design_spaces.fork(id=space.id)
    finally:
        with suppress(NotFoundError):
            client.design_spaces.delete(id=space.id)


@ignore_in_ten0
@builder_not_deployed
def test_create_from_smart_dataset(
    client: Albert, seeded_projects: list[Project], seeded_smart_dataset: SmartDataset
) -> None:
    """Test creating a draft pre-populated from a smart dataset."""
    space = client.design_spaces.create(
        name=f"TEST - derived {uuid.uuid4()}",
        parent_id=seeded_projects[0].id,
        smart_dataset_id=seeded_smart_dataset.id,
    )
    try:
        assert space.state == DesignSpaceState.DRAFT
        assert space.derived_from_id == seeded_smart_dataset.id
    finally:
        with suppress(NotFoundError):
            client.design_spaces.delete(id=space.id)


@ignore_in_ten0
@builder_not_deployed
def test_apply_adds_an_ingredient(client: Albert, seeded_projects: list[Project]) -> None:
    """Test applying a setIngredient operation to a draft."""
    space = _create_space(client, seeded_projects[0].id, "apply ops")
    try:
        result = client.design_spaces.apply(
            id=space.id,
            operations=[
                SetIngredientOperation(
                    key="INV1", value=IngredientEntry(action="mayInclude", min=0.0, max=0.5)
                )
            ],
            validate=True,
            dry_run=False,
        )
        assert isinstance(result, DesignSpaceApplyResponse)
        assert isinstance(result.warnings, list)
    finally:
        with suppress(NotFoundError):
            client.design_spaces.delete(id=space.id)


@ignore_in_ten0
@builder_not_deployed
def test_check_feasibility_returns_a_result(
    client: Albert, seeded_projects: list[Project]
) -> None:
    """Test that feasibility checking returns a structured result."""
    space = _create_space(client, seeded_projects[0].id, "feasibility")
    try:
        result = client.design_spaces.check_feasibility(id=space.id)
        assert isinstance(result, DesignSpaceValidationResponse)
        assert isinstance(result.valid, bool)
    finally:
        with suppress(NotFoundError):
            client.design_spaces.delete(id=space.id)


@ignore_in_ten0
@builder_not_deployed
def test_get_sample_returns_a_sample(client: Albert, seeded_projects: list[Project]) -> None:
    """Test drawing a small sample preview from a draft."""
    space = _create_space(client, seeded_projects[0].id, "sample")
    try:
        sample = client.design_spaces.get_sample(id=space.id, num_samples=2)
        assert isinstance(sample, DesignSpaceSample)
    finally:
        with suppress(NotFoundError):
            client.design_spaces.delete(id=space.id)


@ignore_in_ten0
@builder_not_deployed
def test_publish_then_fork(client: Albert, seeded_projects: list[Project]) -> None:
    """Test publishing a draft and forking the published space into a new draft."""
    space = _create_space(client, seeded_projects[0].id, "publish me")
    forked = None
    try:
        published = client.design_spaces.publish(id=space.id)
        assert published.state == DesignSpaceState.PUBLISHED

        forked = client.design_spaces.fork(id=published.id)
        assert forked.state == DesignSpaceState.DRAFT
        assert forked.forked_from_id == published.id
    finally:
        if forked is not None:
            with suppress(NotFoundError):
                client.design_spaces.delete(id=forked.id)
        with suppress(NotFoundError):
            client.design_spaces.delete(id=space.id)


@ignore_in_ten0
@builder_not_deployed
def test_get_references_returns_a_reference_set(
    client: Albert, seeded_projects: list[Project]
) -> None:
    """Test reading what references a component of a draft."""
    space = _create_space(client, seeded_projects[0].id, "references")
    try:
        references = client.design_spaces.get_references(id=space.id, component="ingredients/INV1")
        assert isinstance(references, DesignSpaceReferences)
    finally:
        with suppress(NotFoundError):
            client.design_spaces.delete(id=space.id)
