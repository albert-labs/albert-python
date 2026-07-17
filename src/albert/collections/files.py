import json
from typing import IO

import requests

from albert.collections.base import BaseCollection
from albert.core.session import AlbertSession
from albert.resources.files import (
    FileCategory,
    FileInfo,
    FileNamespace,
    SignURLPOST,
    SignURLPOSTFile,
)


class FileCollection(BaseCollection):
    """Manage File storage and uploads in the Albert platform.

    This collection is the low-level file storage mechanism behind Albert. Files
    are uploaded to and downloaded from S3-backed storage using short-lived
    signed URLs, and are organized by namespace (see
    [`FileNamespace`][albert.resources.files.FileNamespace]). Files are the underlying
    storage for [`AttachmentCollection`][albert.collections.attachments.AttachmentCollection];
    to attach a file to an entity, upload it here and then create an attachment
    whose ``key`` matches the stored file name. The ``upload_and_attach_*``
    helpers on the attachment collection combine both steps.

    This collection is accessed as ``client.files``.

    !!! example
        ```python
        from albert import Albert
        from albert.resources.files import FileNamespace
        client = Albert()
        with open("results.csv", "rb") as fh:
            client.files.sign_and_upload_file(
                data=fh,
                name="INVA1/results.csv",
                namespace=FileNamespace.RESULT,
                content_type="text/csv",
            )
        ```

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for file requests.

    Methods
    -------
    get_by_name(name, namespace, generic=False) -> FileInfo
        Get stored file metadata by name and namespace.
    get_signed_download_url(name, namespace, ...) -> str
        Get a temporary signed URL to download a file.
    get_signed_upload_url(name, namespace, content_type, ...) -> str
        Get a temporary signed URL to upload a file.
    sign_and_upload_file(data, name, namespace, content_type, ...) -> None
        Sign and upload a file in one step.
    """

    _api_version: str = "v3"

    def __init__(self, *, session: AlbertSession):
        """Initialize a FileCollection.

        Parameters
        ----------
        session : AlbertSession
            The authenticated Albert session used for API calls.
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
        """Get stored file metadata by name and namespace.

        !!! example
            ```python
            from albert.resources.files import FileNamespace
            info = client.files.get_by_name(
                name="INVA1/results.csv", namespace=FileNamespace.RESULT
            )
            info.size
            # 2048
            ```

        Parameters
        ----------
        name : str
            The name (storage key) of the file.
        namespace : FileNamespace
            The namespace the file is stored in (e.g. ``AGENT``, ``BREAKTHROUGH``,
            ``PIPELINE``, ``PUBLIC``, ``RESULT``, ``SDS``).
        generic : bool, optional
            Include generic Albert-managed files in addition to the tenant's own
            files. Defaults to False.

        Returns
        -------
        FileInfo
            Metadata for the matching file.
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
        """Get a temporary signed URL for downloading a file.

        !!! example
            ```python
            from albert.resources.files import FileNamespace
            url = client.files.get_signed_download_url(
                name="INVA1/results.csv", namespace=FileNamespace.RESULT
            )
            ```

        Parameters
        ----------
        name : str
            The name (storage key) of the file.
        namespace : FileNamespace
            The namespace the file is stored in (e.g. ``AGENT``, ``BREAKTHROUGH``,
            ``PIPELINE``, ``PUBLIC``, ``RESULT``, ``SDS``).
        version_id : str | None, optional
            A specific file version to download. Defaults to None (latest).
        generic : bool, optional
            Include generic Albert-managed files in addition to the tenant's own
            files. Defaults to False.
        category : FileCategory | None, optional
            The file category (e.g. ``SDS``, ``OTHER``). Defaults to None.

        Returns
        -------
        str
            A short-lived S3 signed download URL.
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
        """Get a temporary signed URL for uploading a file.

        The returned URL can be used with an HTTP ``PUT`` to upload file contents
        directly to storage. In most cases, prefer [`sign_and_upload_file`][albert.collections.files.FileCollection.sign_and_upload_file],
        which performs both the signing and the upload.

        !!! example
            ```python
            from albert.resources.files import FileNamespace
            url = client.files.get_signed_upload_url(
                name="INVA1/results.csv",
                namespace=FileNamespace.RESULT,
                content_type="text/csv",
            )
            ```

        Parameters
        ----------
        name : str
            The name (storage key) to store the file under.
        namespace : FileNamespace
            The namespace to store the file in (e.g. ``AGENT``, ``BREAKTHROUGH``,
            ``PIPELINE``, ``PUBLIC``, ``RESULT``, ``SDS``).
        content_type : str
            The MIME type of the file (e.g. ``"text/csv"``).
        generic : bool, optional
            Include generic Albert-managed files in addition to the tenant's own
            files. Defaults to False.
        category : FileCategory | None, optional
            The file category (e.g. ``SDS``, ``OTHER``). Defaults to None.

        Returns
        -------
        str
            A short-lived S3 signed upload URL.
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
        """Sign and upload a file to Albert in one step.

        Requests a signed upload URL and streams the file contents to storage.
        This is the primary way to store a file; the resulting stored name can
        then be used as an attachment ``key`` (see
        [`AttachmentCollection`][albert.collections.attachments.AttachmentCollection]).

        !!! example
            ```python
            from albert.resources.files import FileNamespace
            with open("results.csv", "rb") as fh:
                client.files.sign_and_upload_file(
                    data=fh,
                    name="INVA1/results.csv",
                    namespace=FileNamespace.RESULT,
                    content_type="text/csv",
                )
            ```

        Parameters
        ----------
        data : IO
            An open, readable binary file-like object with the file contents.
        name : str
            The name (storage key) to store the file under.
        namespace : FileNamespace
            The namespace to store the file in (e.g. ``AGENT``, ``BREAKTHROUGH``,
            ``PIPELINE``, ``PUBLIC``, ``RESULT``, ``SDS``).
        content_type : str
            The MIME type of the file (e.g. ``"text/csv"``).
        generic : bool, optional
            Include generic Albert-managed files in addition to the tenant's own
            files. Defaults to False.
        category : FileCategory | None, optional
            The category of the file (e.g. ``SDS``, ``OTHER``). Defaults to None.

        Returns
        -------
        None
        """
        upload_url = self.get_signed_upload_url(
            name=name,
            namespace=namespace,
            content_type=content_type,
            generic=generic,
            category=category,
        )
        requests.put(upload_url, data=data, headers={"Content-Type": content_type})
