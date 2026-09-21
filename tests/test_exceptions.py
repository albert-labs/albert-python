import json
import pickle

import pytest
import requests

from albert.exceptions import (
    AlbertClientError,
    AlbertHTTPError,
    AlbertServerError,
    BadRequestError,
    CombinationGenerationError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
    UnauthorizedError,
)
from albert.resources.tasks import PropertyTask


def _make_not_found_response() -> requests.Response:
    """Simulate a 404 returned by the Albert API for a missing project resource."""
    req = requests.PreparedRequest()
    req.method = "GET"
    req.url = "https://app.albertinvent.com/api/v3/projects/PRJ0001"
    req.body = None

    resp = requests.Response()
    resp.status_code = 404
    resp.reason = "Not Found"
    resp.request = req
    resp._content = json.dumps({"errors": "Not Found"}).encode()
    resp.encoding = "utf-8"
    return resp


@pytest.mark.parametrize(
    "exc_cls",
    [
        AlbertHTTPError,
        AlbertClientError,
        BadRequestError,
        UnauthorizedError,
        ForbiddenError,
        NotFoundError,
        AlbertServerError,
        InternalServerError,
    ],
)
def test_albert_http_error_is_picklable(exc_cls):
    """Test that AlbertHTTPError and all subclasses survive a pickle round-trip.

    Python's default exception pickling stores args and calls __init__(*args) on
    unpickle. AlbertHTTPError.__init__ expects a requests.Response, not a string,
    so the default path raises AttributeError. __reduce__ fixes this by
    reconstructing from the pre-formatted message string instead.
    """
    try:
        raise exc_cls(_make_not_found_response())
    except exc_cls as exc:
        original_message = exc.message
        restored = pickle.loads(pickle.dumps(exc))

    assert type(restored) is exc_cls
    assert restored.message == original_message


def test_pickle_preserves_message_content():
    """Test that the Albert API URL, status code, and error body survive pickling."""
    try:
        raise NotFoundError(_make_not_found_response())
    except NotFoundError as exc:
        restored = pickle.loads(pickle.dumps(exc))

    assert "404" in restored.message
    assert "Not Found" in restored.message
    assert "/api/v3/projects/PRJ0001" in restored.message


def test_pickle_sets_response_to_none():
    """Test that response is None after pickling — requests.Response is not serializable."""
    try:
        raise NotFoundError(_make_not_found_response())
    except NotFoundError as exc:
        assert exc.response is not None
        restored = pickle.loads(pickle.dumps(exc))

    assert restored.response is None


def test_combination_generation_error_attributes():
    """Test that CombinationGenerationError preserves task, failed_blocks, and job_states."""
    task = PropertyTask(id="TASFOR123", name="Test Task")
    failed_blocks = ["BLK2", "BLK3"]
    job_states = {"BLK1": "successful", "BLK2": "failed", "BLK3": "failed"}

    err = CombinationGenerationError(
        "Combination generation failed for blocks: BLK2, BLK3",
        task=task,
        failed_blocks=failed_blocks,
        job_states=job_states,
    )

    assert err.task.id == "TASFOR123"
    assert err.failed_blocks == ["BLK2", "BLK3"]
    assert err.job_states == job_states
    assert "Combination generation failed" in str(err)
