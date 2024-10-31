import os
from typing import Union

from pydantic import SecretStr

from albert.utils.types import BaseAlbertModel


class ClientCredentials(BaseAlbertModel):
    """Client authentication credentials for the Albert API."""

    id: str
    secret: SecretStr

    @classmethod
    def from_env(
        cls,
        *,
        client_id_env: str = "ALBERT_CLIENT_ID",
        client_secret_env: str = "ALBERT_CLIENT_SECRET",
    ) -> Union["ClientCredentials", None]:
        """Read `ClientCredentials` from the environment.

        Returns None if the `client_id_env` and `client_secret_env` environment variables
        are not defined.

        Parameters
        ----------
        client_id_env : str
            Name of the environment variable containing the client ID
            (defaults to "ALBERT_CLIENT_ID")
        client_secret_env : str
            Name of the environment variable containing the client secret
            (defaults to "ALBERT_CLIENT_SECRET")

        Returns
        -------
        ClientCredentials | None
            The client credentials obtained from the environment, if present.
        """
        client_id = os.getenv(client_id_env)
        client_secret = os.getenv(client_secret_env)
        if client_id is not None and client_secret is not None:
            return cls(id=client_id, secret=client_secret)
