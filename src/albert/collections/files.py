import json
from typing import IO

import requests

from albert.collections.base import BaseCollection
from albert.resources.files import FileInfo, FileNamespace
from albert.session import AlbertSession


class FileCollection(BaseCollection):
    _api_version: str = "v3"

    def __init__(self, *, session: AlbertSession):
        """
        Initialize the FileCllection with the provided session.

        Parameters
        ----------
        session : AlbertSession
            The Albert session instance.
        """
        super().__init__(session=session)
        self.base_path = f"/api/{FileCollection._api_version}/files"

    def get(self, *, name: str, namespace: FileNamespace, generic: bool = False) -> FileInfo:
        params = {
            "name": name,
            "namespace": namespace,
            "generic": json.dumps(generic),
        }
        response = self.session.get(f"{self.base_path}/info", params=params)
        return FileInfo.model_validate(response.json())

    def get_signed_download_url(
        self,
        *,
        name: str,
        namespace: FileNamespace,
        version_id: str | None = None,
        generic: bool = False,
    ) -> str:
        params = {
            "name": name,
            "namespace": namespace,
            "versionId": version_id,
            "generic": json.dumps(generic),
        }
        response = self.session.get(
            f"{self.base_path}/sign",
            params={k: v for k, v in params.items() if v is not None},
        )
        return response.json()["URL"]

    def get_signed_upload_url(
        self,
        *,
        name: str,
        namespace: FileNamespace,
        content_type: str,
        generic: bool = False,
    ) -> str:
        params = {"generic": json.dumps(generic)}
        body = {
            "files": [
                {
                    "name": name,
                    "namespace": namespace,
                    "contentType": content_type,
                },
            ],
        }
        response = self.session.post(f"{self.base_path}/sign", json=body, params=params)
        return response.json()[0]["URL"]

    def sign_and_upload_file(
        self,
        data: IO,
        name: str,
        namespace: FileNamespace,
        content_type: str,
        generic: bool = False,
    ) -> None:
        upload_url = self.get_signed_upload_url(
            name=name,
            namespace=namespace,
            content_type=content_type,
            generic=generic,
        )
        requests.put(upload_url, data=data, headers={"Content-Type": content_type})
