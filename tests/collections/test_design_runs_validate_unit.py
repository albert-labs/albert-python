import json
from unittest.mock import patch

import pytest
import requests

from albert.client import Albert
from albert.core.session import AlbertSession
from albert.exceptions import AlbertClientError
from albert.resources.design import DesignMethod, DesignRunValidationResponse


def _json_response(*, status: int, body: dict, url: str) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(body).encode()
    response.headers["Content-Type"] = "application/json"
    response.url = url
    response.request = requests.Request("POST", url).prepare()
    return response


@pytest.fixture
def client() -> Albert:
    session = AlbertSession(base_url="https://test.albertinvent.com", token="fake-token", retries=0)
    return Albert(session=session)


def test_validate_returns_parsed_response_on_200_valid_true(client: Albert):
    url = "https://test.albertinvent.com/api/v3/designruns/validate"
    body = {"valid": True, "violations": []}
    with patch(
        "requests.Session.request",
        return_value=_json_response(status=200, body=body, url=url),
    ):
        result = client.design_runs.validate(smart_dataset_id="SDT000001")

    assert isinstance(result, DesignRunValidationResponse)
    assert result.valid is True
    assert result.violations == []


def test_validate_returns_parsed_response_on_200_valid_false(client: Albert):
    url = "https://test.albertinvent.com/api/v3/designruns/validate"
    body = {
        "valid": False,
        "violations": [
            {
                "code": "insufficient_training_data",
                "message": "Only 2 samples",
                "targetId": "TAR000001",
            }
        ],
    }
    with patch(
        "requests.Session.request",
        return_value=_json_response(status=200, body=body, url=url),
    ):
        result = client.design_runs.validate(smart_dataset_id="SDT000001")

    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].target_id == "TAR000001"


def test_validate_raises_on_422_precheck(client: Albert):
    url = "https://test.albertinvent.com/api/v3/designruns/validate"
    body = {
        "status": 422,
        "title": "Unprocessable Entity",
        "errors": [{"msg": "Smart dataset SDT000001 is not ready (build_state=BUILDING)."}],
    }
    with patch(
        "requests.Session.request",
        return_value=_json_response(status=422, body=body, url=url),
    ):
        with pytest.raises(AlbertClientError, match="422"):
            client.design_runs.validate(smart_dataset_id="SDT000001")


def test_validate_posts_to_validate_subpath(client: Albert):
    url = "https://test.albertinvent.com/api/v3/designruns/validate"
    with patch(
        "requests.Session.request",
        return_value=_json_response(status=200, body={"valid": True, "violations": []}, url=url),
    ) as mock_request:
        client.design_runs.validate(
            smart_dataset_id="SDT000001",
            method=DesignMethod.GENERATE,
        )

    mock_request.assert_called_once()
    call_args = mock_request.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1].endswith("/api/v3/designruns/validate")
    assert call_args[1]["json"] == {"smartDatasetId": "SDT000001", "method": "generate"}
