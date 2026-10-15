from collections.abc import Callable, Iterator
from typing import Any

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.core.shared.identifiers import DesignSpaceId, ProjectId, SmartDatasetId
from albert.resources.design_spaces import (
    CreateDesignSpaceRequest,
    DesignSpace,
    DesignSpaceApplyResponse,
    DesignSpaceForkRequest,
    DesignSpaceOperation,
    DesignSpaceOperationsRequest,
    DesignSpacePreviewRequest,
    DesignSpaceReferences,
    DesignSpaceSample,
    DesignSpaceSampleRequest,
    DesignSpaceState,
    DesignSpaceValidationRequest,
    DesignSpaceValidationResponse,
)


def _iter_last_key_pages(
    fetch_page: Callable[[str | None], dict[str, Any]],
    *,
    max_items: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield raw items across ``lastKey`` cursor pages.

    ``fetch_page`` is called with the cursor of the previous page (``None`` for the
    first page) and returns one decoded page. A page whose ``lastKey`` repeats a key
    already seen is dropped wholesale, so a misbehaving cursor cannot loop forever.
    """
    seen_cursors: set[str] = set()
    cursor: str | None = None
    yielded = 0
    while True:
        data = fetch_page(cursor)
        next_cursor = data.get("lastKey")
        if next_cursor is not None:
            if next_cursor in seen_cursors:
                return
            seen_cursors.add(next_cursor)
        for item in data.get("items") or []:
            if max_items is not None and yielded >= max_items:
                return
            yield item
            yielded += 1
        if next_cursor is None:
            return
        cursor = next_cursor


class DesignSpaceCollection(BaseCollection):
    """Manage Design Spaces in the Albert platform (🧪 Beta).

    A design space is the bounded envelope (also called the search space) that a design
    run samples formulations from: which ingredients may or must appear, the fraction
    bounds on each, the allowed values of parameters, and how many ingredients one
    formulation may carry.

    A space is created as a draft, edited with builder operations, checked for
    feasibility, and published. A published space is frozen; editing one means forking
    it into a new draft.

    This collection is accessed as ``client.design_spaces``.

    !!! warning "Beta Feature!"
        Please do not use in production or without explicit guidance from Albert. You might otherwise have a bad experience.
        This feature currently falls outside of the Albert support contract, but we'd love your feedback!

    !!! example
        ```python
        from albert import Albert

        client = Albert()
        space = client.design_spaces.create(
            name="Low-VOC clearcoat envelope",
            parent_id="PRO123",
        )
        space.state
        # <DesignSpaceState.DRAFT: 'draft'>
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for design-space requests.

    Methods
    -------
    create(name, parent_id, description=None, smart_dataset_id=None) -> DesignSpace
        Create a draft design space, empty or seeded from a smart dataset.
    get_by_id(id) -> DesignSpace
        Get a single design space by its ID.
    get_all(parent_id, state=None, max_items=None) -> Iterator[DesignSpace]
        Get all design spaces in a project.
    update(design_space) -> DesignSpace
        Update the name or description of a draft design space.
    apply(id, operations, validate=False, preview=None, dry_run=False) -> DesignSpaceApplyResponse
        Apply builder operations to a draft design space.
    check_feasibility(id, smart_dataset_id=None, design_model_config_id=None) -> DesignSpaceValidationResponse
        Check whether a design space can produce valid formulations.
    get_sample_preview(id, num_samples=10) -> DesignSpaceSample
        Get a sample of the formulations a design space would produce.
    publish(id) -> DesignSpace
        Publish a draft design space, freezing it for use by design runs.
    fork(id, parent_id=None) -> DesignSpace
        Fork a published design space into a new editable draft.
    get_references(id, component) -> DesignSpaceReferences
        Get what references a component of a design space.
    delete(id) -> None
        Delete a design space by its ID.
    """

    _api_version = "v4.0"
    _updatable_attributes = {"name", "description"}
    _non_deletable_attributes = {"name"}

    def __init__(self, *, session: AlbertSession):
        super().__init__(session=session)
        self.base_path = f"/api/{DesignSpaceCollection._api_version}/design/design-spaces"

    @validate_call
    def create(
        self,
        *,
        name: str,
        parent_id: ProjectId,
        description: str | None = None,
        smart_dataset_id: SmartDatasetId | None = None,
    ) -> DesignSpace:
        """Create a draft design space.

        A design space (also called an envelope or search space) bounds what a design
        run may propose: the ingredients and their fraction bounds, the allowed
        parameter values, and the ingredient-count bounds.

        Pass ``smart_dataset_id`` to pre-populate the draft from a smart dataset's
        observed dimensions; omit it to start empty and add dimensions with
        [`apply`][albert.collections.design_spaces.DesignSpaceCollection.apply].

        !!! example
            ```python
            space = client.design_spaces.create(
                name="Low-VOC clearcoat envelope",
                parent_id="PRO123",
                description="Regulatory envelope for the 2027 EU clearcoat line.",
            )
            ```

        Parameters
        ----------
        name : str
            Display name of the design space.
        parent_id : ProjectId
            The project (format ``PRO...``) that owns the space and controls access to it.
        description : str, optional
            Free-text description of the space's intent.
        smart_dataset_id : SmartDatasetId, optional
            Smart dataset (format ``SDT...``) whose contents seed the first draft. Omit
            for an empty draft.

        Returns
        -------
        DesignSpace
            The created draft design space.
        """
        body = CreateDesignSpaceRequest(
            name=name,
            parent_id=parent_id,
            description=description,
            smart_dataset_id=smart_dataset_id,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(self.base_path, json=body)
        return DesignSpace(**response.json())

    @validate_call
    def get_by_id(self, *, id: DesignSpaceId) -> DesignSpace:
        """Get a single design space by its ID.

        !!! example
            ```python
            space = client.design_spaces.get_by_id(id="DSP123")
            space.name
            # 'Low-VOC clearcoat envelope'
            ```

        Parameters
        ----------
        id : DesignSpaceId
            The design space ID (format ``DSP...``).

        Returns
        -------
        DesignSpace
            The fully populated design space.
        """
        response = self.session.get(f"{self.base_path}/{id}")
        return DesignSpace(**response.json())

    @validate_call
    def get_all(
        self,
        *,
        parent_id: ProjectId,
        state: DesignSpaceState | None = None,
        max_items: int | None = None,
    ) -> Iterator[DesignSpace]:
        """Get all design spaces in a project.

        Results are returned as a lazily paginated iterator.

        !!! example
            ```python
            for space in client.design_spaces.get_all(parent_id="PRO123"):
                print(space.id, space.name, space.state)
            ```

        Parameters
        ----------
        parent_id : ProjectId
            The project (format ``PRO...``) whose spaces to list.
        state : DesignSpaceState, optional
            Limit to drafts or to published spaces.
        max_items : int, optional
            Stop after this many spaces.

        Returns
        -------
        Iterator[DesignSpace]
            A lazily paginated iterator over the project's design spaces.
        """
        params: dict[str, Any] = {"parentId": parent_id, "state": state}

        def fetch_page(cursor: str | None) -> dict[str, Any]:
            return self.session.get(self.base_path, params={**params, "lastKey": cursor}).json()

        return (
            DesignSpace(**item) for item in _iter_last_key_pages(fetch_page, max_items=max_items)
        )

    @validate_call
    def update(self, *, design_space: DesignSpace) -> DesignSpace:
        """Update the name or description of a draft design space.

        Retrieve the space with
        [`get_by_id`][albert.collections.design_spaces.DesignSpaceCollection.get_by_id],
        modify ``name`` and/or ``description``, then pass it here. Only changed fields
        are applied.

        A published space is frozen and cannot be updated;
        [`fork`][albert.collections.design_spaces.DesignSpaceCollection.fork] it into a
        new draft instead.

        !!! example
            ```python
            space = client.design_spaces.get_by_id(id="DSP123")
            space.description = "Regulatory envelope for the 2027 EU clearcoat line, rev B"
            updated = client.design_spaces.update(design_space=space)
            ```

        Parameters
        ----------
        design_space : DesignSpace
            The design space carrying the desired changes. Its ``id`` identifies which
            space to update.

        Returns
        -------
        DesignSpace
            The updated design space.

        Notes
        -----
        The following fields can be updated: ``name``, ``description``.
        """
        existing = self.get_by_id(id=design_space.id)
        patch_payload = self._generate_patch_payload(
            existing=existing, updated=design_space
        ).model_dump(mode="json", by_alias=True)
        if not patch_payload["data"]:
            return existing
        response = self.session.patch(f"{self.base_path}/{design_space.id}", json=patch_payload)
        return DesignSpace(**response.json())

    @validate_call
    def apply(
        self,
        *,
        id: DesignSpaceId,
        operations: list[DesignSpaceOperation],
        validate: bool = False,
        preview: int | None = None,
        dry_run: bool = False,
    ) -> DesignSpaceApplyResponse:
        """Apply builder operations to a draft design space.

        Operations apply atomically and in the order given; if one cannot apply (for
        example an unknown reference or an invalid constraint) nothing is applied. The
        five operations:

        - [`SetIngredientOperation`][albert.resources.design_spaces.SetIngredientOperation]:
          upsert an ingredient. Its value carries the three-way action (must include,
          may include, or exclude) and the ingredient's fraction bounds.
        - [`SetParameterOperation`][albert.resources.design_spaces.SetParameterOperation]:
          upsert a parameter with its allowed values.
        - [`SetCountBoundsOperation`][albert.resources.design_spaces.SetCountBoundsOperation]:
          set or clear the ingredient-count bounds.
        - [`RemoveComponentOperation`][albert.resources.design_spaces.RemoveComponentOperation]:
          remove an ingredient or parameter by its path.
        - [`UpdateComponentOperation`][albert.resources.design_spaces.UpdateComponentOperation]:
          change one field of a component in place.

        !!! example
            ```python
            from albert.resources.design_spaces import IngredientEntry, SetIngredientOperation

            result = client.design_spaces.apply(
                id="DSP123",
                operations=[
                    SetIngredientOperation(
                        key="INV004",
                        value=IngredientEntry(action="mayInclude", min=0.0, max=0.03),
                    )
                ],
                validate=True,
            )
            result.validation.valid
            # True
            ```

        Parameters
        ----------
        id : DesignSpaceId
            The design space ID (format ``DSP...``).
        operations : list[DesignSpaceOperation]
            The operations to apply, in order.
        validate : bool, optional
            Fold a feasibility check into the result. An infeasible outcome is a normal
            result with ``validation.valid == False``, not an exception.
        preview : int, optional
            Fold a sample preview of this many formulations (1 to 25) into the result.
        dry_run : bool, optional
            Compute the would-be result without saving it.

        Returns
        -------
        DesignSpaceApplyResponse
            The resulting design space, any non-blocking findings, and the feasibility
            check and sample preview when asked for.

        Raises
        ------
        AlbertClientError
            An operation could not apply (unknown reference, invalid constraint, or a
            conflicting edit), or the space is published.
        AlbertHTTPError
            Other failures.
        """
        body = DesignSpaceOperationsRequest(
            operations=operations,
            validate_=validate,
            preview=(
                DesignSpacePreviewRequest(num_samples=preview) if preview is not None else None
            ),
            dry_run=dry_run,
        ).model_dump(
            by_alias=True,
            mode="json",
            # setCountBounds clears a bound with an explicit None, so unset fields
            # (leave unchanged) must be dropped while explicit Nones survive.
            exclude_unset=True,
        )
        response = self.session.post(f"{self.base_path}/{id}/operations", json=body)
        return DesignSpaceApplyResponse(**response.json())

    @validate_call
    def check_feasibility(
        self,
        *,
        id: DesignSpaceId,
        smart_dataset_id: SmartDatasetId | None = None,
        design_model_config_id: str | None = None,
    ) -> DesignSpaceValidationResponse:
        """Check whether a design space can produce valid formulations.

        Feasibility needs no dataset; pass ``smart_dataset_id`` and/or
        ``design_model_config_id`` to additionally check the space against that
        context. ``valid=False`` with populated ``violations`` is a normal result, not
        an exception. A solver timeout is reported as the ``feasibility_indeterminate``
        violation, meaning the answer is unknown rather than infeasible.

        !!! example
            ```python
            result = client.design_spaces.check_feasibility(id="DSP123")
            if not result.valid:
                for violation in result.violations:
                    print(violation.code, violation.message)
            ```

        Parameters
        ----------
        id : DesignSpaceId
            The design space ID (format ``DSP...``).
        smart_dataset_id : SmartDatasetId, optional
            Also check the space against this smart dataset (format ``SDT...``).
        design_model_config_id : str, optional
            Also check the space against this design model config.

        Returns
        -------
        DesignSpaceValidationResponse
            The feasibility result with ``valid`` and ``violations``.
        """
        body = DesignSpaceValidationRequest(
            smart_dataset_id=smart_dataset_id,
            design_model_config_id=design_model_config_id,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        response = self.session.post(f"{self.base_path}/{id}/validation", json=body)
        return DesignSpaceValidationResponse(**response.json())

    @validate_call
    def get_sample_preview(
        self,
        *,
        id: DesignSpaceId,
        num_samples: int = 10,
    ) -> DesignSpaceSample:
        """Get a sample of the formulations a design space would produce.

        A quick preview of the envelope (search space), for inspecting what the bounds
        allow before committing a design run to them.

        !!! example
            ```python
            sample = client.design_spaces.get_sample_preview(id="DSP123", num_samples=5)
            ```

        Parameters
        ----------
        id : DesignSpaceId
            The design space ID (format ``DSP...``).
        num_samples : int, optional
            Number of formulations to draw (1 to 25, default 10).

        Returns
        -------
        DesignSpaceSample
            The drawn sample.
        """
        body = DesignSpaceSampleRequest(num_samples=num_samples).model_dump(
            by_alias=True, mode="json", exclude_none=True
        )
        response = self.session.post(f"{self.base_path}/{id}/samples", json=body)
        return DesignSpaceSample(**response.json())

    @validate_call
    def publish(self, *, id: DesignSpaceId) -> DesignSpace:
        """Publish a draft design space, freezing it for use by design runs.

        The space is validated first: an infeasible space cannot be published, and an
        already-published space conflicts. Published spaces are immutable; to change
        one, [`fork`][albert.collections.design_spaces.DesignSpaceCollection.fork] it
        into a new draft.

        !!! example
            ```python
            published = client.design_spaces.publish(id="DSP123")
            published.state
            # <DesignSpaceState.PUBLISHED: 'published'>
            ```

        Parameters
        ----------
        id : DesignSpaceId
            The design space ID (format ``DSP...``).

        Returns
        -------
        DesignSpace
            The published design space.

        Raises
        ------
        AlbertClientError
            The space is infeasible (the blocking violations are listed) or already
            published.
        AlbertHTTPError
            Other failures.
        """
        response = self.session.post(f"{self.base_path}/{id}/publication")
        return DesignSpace(**response.json())

    @validate_call
    def fork(self, *, id: DesignSpaceId, parent_id: ProjectId | None = None) -> DesignSpace:
        """Fork a published design space into a new editable draft.

        The new draft remembers which published space it came from
        (``forked_from_id``). Forking a draft conflicts; only published spaces can be
        forked.

        !!! example
            ```python
            draft = client.design_spaces.fork(id="DSP123")
            draft.state
            # <DesignSpaceState.DRAFT: 'draft'>
            ```

        Parameters
        ----------
        id : DesignSpaceId
            The published design space ID (format ``DSP...``).
        parent_id : ProjectId, optional
            Target project (format ``PRO...``) for the fork. Omit to keep the source's
            project.

        Returns
        -------
        DesignSpace
            The new draft design space.
        """
        body = DesignSpaceForkRequest(parent_id=parent_id).model_dump(
            by_alias=True, mode="json", exclude_none=True
        )
        response = self.session.post(f"{self.base_path}/{id}/forks", json=body)
        return DesignSpace(**response.json())

    @validate_call
    def get_references(self, *, id: DesignSpaceId, component: str) -> DesignSpaceReferences:
        """Get what references a component of a design space.

        Powers safe removal: check whether anything still points at the component
        before removing it with
        [`apply`][albert.collections.design_spaces.DesignSpaceCollection.apply].

        !!! example
            ```python
            refs = client.design_spaces.get_references(
                id="DSP123", component="ingredients/INV004"
            )
            ```

        Parameters
        ----------
        id : DesignSpaceId
            The design space ID (format ``DSP...``).
        component : str
            Component path, ``<collection>/<key>`` (e.g. ``"ingredients/INV004"``).

        Returns
        -------
        DesignSpaceReferences
            The references to the component.
        """
        response = self.session.get(
            f"{self.base_path}/{id}/references", params={"component": component}
        )
        return DesignSpaceReferences(**response.json())

    @validate_call
    def delete(self, *, id: DesignSpaceId) -> None:
        """Delete a design space by its ID.

        A published space that a design run still references cannot be deleted.

        !!! example
            ```python
            client.design_spaces.delete(id="DSP123")
            ```

        Parameters
        ----------
        id : DesignSpaceId
            The design space ID (format ``DSP...``).

        Returns
        -------
        None
        """
        self.session.delete(f"{self.base_path}/{id}")
