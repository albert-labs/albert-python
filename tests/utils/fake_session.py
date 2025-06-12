from typing import Any

import requests


class FakeAlbertSession(requests.Session):
    """Fake implementation of Albert API session for testing."""

    def __init__(self):
        """Initialize the fake session."""
        super().__init__()
        self.requests: list[dict[str, Any]] = []
        self.responses: dict[str, Any] = {}

    def request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Make a fake request to the Albert API.

        Parameters
        ----------
        method : str
            The HTTP method to use (GET, POST, etc.)
        url : str
            The URL to request
        params : Optional[Dict[str, Any]], optional
            Query parameters to include in the request, by default None
        json : Optional[Dict[str, Any]], optional
            JSON body to include in the request, by default None
        **kwargs : Any
            Additional arguments to pass to requests

        Returns
        -------
        requests.Response
            A fake response with the configured data
        """
        # Record the request
        self.requests.append(
            {"method": method, "url": url, "params": params, "json": json, **kwargs}
        )

        # Create a fake response
        response = requests.Response()
        response.status_code = 200

        # Get the configured response data
        key = f"{method}:{url}"
        if key in self.responses:
            response_data = self.responses[key]
            if isinstance(response_data, Exception):
                raise response_data
            response._content = response_data
        else:
            response._content = b"{}"

        return response

    def configure_response(self, method: str, url: str, response_data: Any) -> None:
        """Configure the response for a specific request.

        Parameters
        ----------
        method : str
            The HTTP method
        url : str
            The URL
        response_data : Any
            The response data to return
        """
        key = f"{method}:{url}"
        self.responses[key] = response_data
