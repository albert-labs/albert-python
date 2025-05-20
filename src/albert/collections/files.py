import json
from typing import IO

import requests

from albert.collections.base import BaseCollection
from albert.resources.files import (
    FileCategory,
    FileInfo,
    FileNamespace,
    SignURLPOST,
    SignURLPOSTFile,
)
from albert.session import AlbertSession


class FileCollection(BaseCollection):
    """FileCollection is a collection class for managing File entities in the Albert platform."""

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

    def get_by_name(
        self,
        *,
        name: str,
        namespace: FileNamespace,
        generic: bool = False,
    ) -> FileInfo:
        """Gets a file by name and namespace.

        Parameters
        ----------
        name : str
            The Name of the file
        namespace : FileNamespace
            The namespace of the file (e.g. AGENT, BREAKTHROUGH, PIPELINE, PUBLIC, RESULT, SDS)
        generic : bool, optional
            _description_, by default False

        Returns
        -------
        FileInfo
            The file information related to the matching file.
        """
        params = {
            "name": name,
            "namespace": namespace,
            "generic": json.dumps(generic),
        }
        response = self.session.get(f"{self.base_path}/info", params=params)
        return FileInfo(**response.json())

    def get_signed_download_url(
        self,
        *,
        name: str,
        namespace: FileNamespace,
        version_id: str | None = None,
        generic: bool = False,
        category: FileCategory | None = None,
    ) -> str:
        """Get a signed download URL for a file.

        Parameters
        ----------
        name : str
            The Name of the file
        namespace : FileNamespace
            The namespace of the file (e.g. AGENT, BREAKTHROUGH, PIPELINE, PUBLIC, RESULT, SDS)
        version_id : str | None, optional
            The version of the file, by default None
        category : FileCategory | None, optional
            The file category (E.g., SDS, OTHER), by default None

        Returns
        -------
        str
            _description_
        """
        params = {
            "name": name,
            "namespace": namespace,
            "versionId": version_id,
            "generic": json.dumps(generic),
            "category": category,
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
        category: FileCategory | None = None,
    ) -> str:
        """Get a signed upload URL for a file.

        Parameters
        ----------
        name : str
            The Name of the file
        namespace : FileNamespace
            The namespace of the file (e.g. AGENT, BREAKTHROUGH, PIPELINE, PUBLIC, RESULT, SDS)
        content_type : str
            The content type of the file
        category : FileCategory | None, optional
            The File category (E.g., SDS, OTHER), by default None

        Returns
        -------
        str
            _description_
        """
        params = {"generic": json.dumps(generic)}

        post_body = SignURLPOST(
            files=[
                SignURLPOSTFile(
                    name=name,
                    namespace=namespace,
                    content_type=content_type,
                    category=category,
                )
            ]
        )

        response = self.session.post(
            f"{self.base_path}/sign",
            json=post_body.model_dump(by_alias=True, exclude_unset=True, mode="json"),
            params=params,
        )
        return response.json()[0]["URL"]

    def sign_and_upload_file(
        self,
        data: IO,
        name: str,
        namespace: FileNamespace,
        content_type: str,
        generic: bool = False,
        category: FileCategory | None = None,
    ) -> None:
        """Sign and upload a file to Albert.

        Parameters
        ----------
        data : IO
            The file data
        name : str
            The name of the file
        namespace : FileNamespace
            The File Namespace (e.g., AGENT, BREAKTHROUGH, PIPELINE, PUBLIC, RESULT, SDS)
        content_type : str
            The content type of the file
        category : FileCategory | None, optional
            The category of the file (E.g., SDS, OTHER), by default None
        """
        upload_url = self.get_signed_upload_url(
            name=name,
            namespace=namespace,
            content_type=content_type,
            generic=generic,
            category=category,
        )
        requests.put(upload_url, data=data, headers={"Content-Type": content_type})
