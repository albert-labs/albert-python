import mimetypes
import uuid
from datetime import date
from pathlib import Path
from typing import IO

from pydantic import validate_call

from albert.collections.base import BaseCollection
from albert.collections.files import FileCollection
from albert.collections.notes import NotesCollection
from albert.core.shared.identifiers import AttachmentId, DataColumnId, InventoryId, ProjectId
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.core.shared.types import MetadataItem
from albert.resources.attachments import (
    Attachment,
    AttachmentCategory,
    AttachmentMetadata,
)
from albert.resources.files import FileCategory, FileNamespace
from albert.resources.hazards import HazardStatement, HazardSymbol
from albert.resources.notes import Note


class AttachmentCollection(BaseCollection):
    """Manage Attachments in the Albert platform.

    An Attachment links an uploaded file to a parent entity (its ``parent_id``),
    such as a Task, Project, Inventory Item, or Note. The file itself is stored
    and uploaded through the [`FileCollection`][albert.collections.files.FileCollection];
    an Attachment is the record that associates that stored file with an entity.
    A common pattern is to upload a file and attach it in one step using the
    ``upload_and_attach_*`` helpers below.

    This collection is accessed as ``client.attachments``.

    Parameters
    ----------
    session : AlbertSession
        The authenticated Albert session used for API calls.

    Attributes
    ----------
    base_path : str
        The base API route for attachment requests.

    Methods
    -------
    create(attachment) -> Attachment
        Create an attachment record for an already-uploaded file.
    get_by_id(id) -> Attachment
        Retrieve a single attachment by its ID.
    get_by_parent_ids(parent_ids, data_column_ids=None) -> dict[str, list[Attachment]]
        Retrieve attachments grouped by parent entity ID.
    update(attachment) -> Attachment
        Apply changes to an existing attachment.
    delete(id) -> None
        Delete an attachment by its ID.
    attach_file_to_note(note_id, file_name, file_key, category=FileCategory.OTHER) -> Attachment
        Attach an already-uploaded file to a note.
    upload_and_attach_file_as_note(parent_id, file_data, ...) -> Note
        Upload a file and attach it to a new note on a parent entity.
    upload_and_attach_sds_to_inventory_item(inventory_id, file_sds, ...) -> Attachment
        Upload an SDS document and attach it to an inventory item.
    upload_and_attach_document_to_project(project_id, file_path) -> Attachment
        Upload a file and attach it as a document to a project.
    get_jurisdiction_codes() -> dict[str, str]
        Retrieve available SDS jurisdiction codes.
    get_language_codes() -> dict[str, str]
        Retrieve available SDS language codes.

    !!! example
        ```python
        from albert import Albert
        client = Albert()
        attachments = client.attachments.get_by_parent_ids(parent_ids=["INVA1"])
        for attachment in attachments.get("INVA1", []):
            print(attachment.name)
        ```
    """

    _api_version: str = "v3"
    _updatable_attributes = {"name", "revision_date", "parent_id"}
    _updatable_metadata_attributes = {
        "Symbols",
        "unNumber",
        "storageClass",
        "hazardStatement",
        "jurisdictionCode",
        "languageCode",
        "wgk",
        "description",
        "extensions",
    }

    def __init__(self, *, session):
        super().__init__(session=session)
        self.base_path = f"/api/{AttachmentCollection._api_version}/attachments"

    def _get_file_collection(self):
        return FileCollection(session=self.session)

    def _get_note_collection(self):
        return NotesCollection(session=self.session)

    @validate_call
    def get_by_id(self, *, id: AttachmentId) -> Attachment:
        """Retrieve an attachment by its ID.

        Parameters
        ----------
        id : AttachmentId
            The Attachment ID (format ``ATT...``).

        Returns
        -------
        Attachment
            The matching attachment.

        !!! example
            ```python
            attachment = client.attachments.get_by_id(id="ATT1")
            attachment.name
            # 'sds.pdf'
            ```
        """
        response = self.session.get(url=f"{self.base_path}/{id}")
        return Attachment(**response.json())

    @validate_call
    def create(self, *, attachment: Attachment) -> Attachment:
        """Create an attachment record for an already-uploaded file.

        Use this when the underlying file has already been uploaded via the
        [`FileCollection`][albert.collections.files.FileCollection]; the attachment's
        ``key`` should match the stored [`name`][albert.resources.files.FileInfo.name].
        To upload and attach in a single call, use one of the
        ``upload_and_attach_*`` helpers instead.

        Parameters
        ----------
        attachment : Attachment
            The attachment to create. Requires ``parent_id``, ``name``, and
            ``key``.

        Returns
        -------
        Attachment
            The created attachment.

        !!! example
            ```python
            from albert.resources.attachments import Attachment
            attachment = client.attachments.create(
                attachment=Attachment(
                    parent_id="INVA1",
                    name="datasheet.pdf",
                    key="INVA1/documents/datasheet.pdf",
                )
            )
            ```
        """
        payload = attachment.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = self.session.post(self.base_path, json=payload)
        return Attachment(**response.json())

    @validate_call
    def update(self, *, attachment: Attachment) -> Attachment:
        """Update an attachment.

        Parameters
        ----------
        attachment : Attachment
            The attachment with updated fields. Must include ``id``.

        Returns
        -------
        Attachment
            The updated Attachment.

        Notes
        -----
        The following fields can be updated: ``name``, ``parent_id``, ``revision_date``.
        Metadata fields such as hazard symbols, hazard statements, storage class,
        UN number, jurisdiction code, and language code can also be updated.

        !!! example
            ```python
            attachment = client.attachments.get_by_id(id="ATT1")
            attachment.name = "renamed.pdf"
            updated = client.attachments.update(attachment=attachment)
            ```
        """
        if attachment.id is None:
            raise ValueError("Attachment ID is required for update.")

        existing_attachment = self.get_by_id(id=attachment.id)
        payload = self._generate_attachment_patch_payload(
            existing=existing_attachment, updated=attachment
        )
        if len(payload.data) == 0:
            return existing_attachment

        # The API rejects more than one operation on the same list attribute
        # (e.g. Symbols) in a single request, so each such op is sent separately.
        list_attrs = {
            d.attribute
            for d in payload.data
            if isinstance(d.old_value, list) or isinstance(d.new_value, list)
        }
        scalar_data = [d for d in payload.data if d.attribute not in list_attrs]
        list_data = [d for d in payload.data if d.attribute in list_attrs]
        batches = [scalar_data] if scalar_data else []
        batches.extend([d] for d in list_data)
        for batch in batches:
            self.session.patch(
                f"{self.base_path}/{attachment.id}",
                json=PatchPayload(data=batch).model_dump(by_alias=True, mode="json"),
            )
        return self.get_by_id(id=attachment.id)

    def _generate_attachment_patch_payload(
        self, *, existing: Attachment, updated: Attachment
    ) -> PatchPayload:
        # Diff top-level fields (name, revision_date, parent_id)
        patch_data: list[PatchDatum] = list(
            self._generate_patch_payload(
                existing=existing,
                updated=updated,
                generate_metadata_diff=False,
            ).data
        )

        if "metadata" not in updated.model_fields_set:
            return PatchPayload(data=patch_data)

        existing_meta = existing.metadata or AttachmentMetadata()
        updated_meta = updated.metadata or AttachmentMetadata()

        existing_dump = existing_meta.model_dump(by_alias=True, mode="json")
        updated_dump = updated_meta.model_dump(by_alias=True, mode="json")

        for attribute in self._updatable_metadata_attributes:
            old_value = existing_dump.get(attribute)
            new_value = updated_dump.get(attribute)

            if isinstance(old_value, list) or isinstance(new_value, list):
                # Diff list fields item-by-item using id. The Symbols field requires
                # the patch value wrapped as [{"id": ...}].
                old_ids = [x["id"] for x in (old_value or [])]
                new_ids = [x["id"] for x in (new_value or [])]
                for item_id in old_ids:
                    if item_id not in new_ids:
                        patch_data.append(
                            PatchDatum(
                                attribute=attribute,
                                operation=PatchOperation.DELETE,
                                old_value=[{"id": item_id}] if attribute == "Symbols" else item_id,
                            )
                        )
                for item_id in new_ids:
                    if item_id not in old_ids:
                        patch_data.append(
                            PatchDatum(
                                attribute=attribute,
                                operation=PatchOperation.ADD,
                                new_value=[{"id": item_id}] if attribute == "Symbols" else item_id,
                            )
                        )
            else:
                # Diff scalar fields
                if old_value is None and new_value is not None:
                    patch_data.append(
                        PatchDatum(
                            attribute=attribute, operation=PatchOperation.ADD, new_value=new_value
                        )
                    )
                elif old_value is not None and new_value is None:
                    patch_data.append(
                        PatchDatum(
                            attribute=attribute,
                            operation=PatchOperation.DELETE,
                            old_value=old_value,
                        )
                    )
                elif old_value is not None and new_value != old_value:
                    patch_data.append(
                        PatchDatum(
                            attribute=attribute,
                            operation=PatchOperation.UPDATE,
                            old_value=old_value,
                            new_value=new_value,
                        )
                    )

        return PatchPayload(data=patch_data)

    def get_by_parent_ids(
        self, *, parent_ids: list[str], data_column_ids: list[DataColumnId] | None = None
    ) -> dict[str, list[Attachment]]:
        """Retrieves attachments by their parent IDs.

        Note: This method returns a dictionary where the keys are parent IDs
        and the values are lists of Attachment objects associated with each parent ID.
        If the parent ID has no attachments, it will not be included in the dictionary.

        If no attachments are found for any of the provided parent IDs,
        the API response will be an error.

        Parameters
        ----------
        parent_ids : list[str]
            Parent IDs of the objects to which the attachments are linked. IDs must
            include the full entity prefix (e.g. ``"INVA123"`` for an inventory item,
            ``"PRO123"`` for a project).

        data_column_ids : list[DataColumnId] | None, optional
            Restrict results to attachments linked through the given data columns
            (format ``DAC...``). Defaults to None (no data-column filter).

        Returns
        -------
        dict[str, list[Attachment]]
            A dictionary mapping parent IDs to lists of Attachment objects associated with each parent ID.

        !!! example
            ```python
            by_parent = client.attachments.get_by_parent_ids(parent_ids=["INVA1", "PROA1"])
            by_parent.get("INVA1", [])
            # [Attachment(...), ...]
            ```
        """
        response = self.session.get(
            url=f"{self.base_path}/parents",
            params={"id": parent_ids, "dataColumnId": data_column_ids},
        )
        response_data = response.json()
        return {
            parent["parentId"]: [
                Attachment(**item, parent_id=parent["parentId"]) for item in parent["Items"]
            ]
            for parent in response_data
        }

    def attach_file_to_note(
        self,
        *,
        note_id: str,
        file_name: str,
        file_key: str,
        category: FileCategory = FileCategory.OTHER,
    ) -> Attachment:
        """Attaches an already uploaded file to a note.

        Parameters
        ----------
        note_id : str
            The ID of the note to attach the file to.
        file_name : str
            The name of the file to attach.
        file_key : str
            The unique key of the file to attach (the returned upload name).
        category : FileCategory, optional
            The type of file. Defaults to ``FileCategory.OTHER``.

        Returns
        -------
        Attachment
            The created attachment linking the file to the note.

        !!! example
            ```python
            attachment = client.attachments.attach_file_to_note(
                note_id="...",
                file_name="results.csv",
                file_key="INVA1/notes/results.csv",
            )
            ```
        """
        attachment = Attachment(
            parent_id=note_id, name=file_name, key=file_key, namespace="result", category=category
        )
        return self.create(attachment=attachment)

    def get_jurisdiction_codes(self) -> dict[str, str]:
        """Return available SDS jurisdiction codes.

        Useful for supplying ``jurisdiction_code`` to
        [`upload_and_attach_sds_to_inventory_item`][albert.collections.attachments.AttachmentCollection.upload_and_attach_sds_to_inventory_item].

        Returns
        -------
        dict[str, str]
            Mapping of jurisdiction name to code (e.g. ``{"Germany": "DE", "USA": "US"}``).

        !!! example
            ```python
            codes = client.attachments.get_jurisdiction_codes()
            codes["USA"]
            # 'US'
            ```
        """
        response = self.session.get(
            f"{self.base_path}/jurisdictionslanguages", params={"type": "jurisdiction"}
        )
        return response.json()

    def get_language_codes(self) -> dict[str, str]:
        """Return available SDS language codes.

        Useful for supplying ``language_code`` to
        [`upload_and_attach_sds_to_inventory_item`][albert.collections.attachments.AttachmentCollection.upload_and_attach_sds_to_inventory_item].

        Returns
        -------
        dict[str, str]
            Mapping of language name to code (e.g. ``{"English": "EN", "German": "DE"}``).

        !!! example
            ```python
            codes = client.attachments.get_language_codes()
            codes["English"]
            # 'EN'
            ```
        """
        response = self.session.get(
            f"{self.base_path}/jurisdictionslanguages", params={"type": "language"}
        )
        return response.json()

    @validate_call
    def delete(self, *, id: AttachmentId) -> None:
        """Delete an attachment by its ID.

        Parameters
        ----------
        id : AttachmentId
            The Attachment ID to delete (format ``ATT...``).

        Returns
        -------
        None

        !!! example
            ```python
            client.attachments.delete(id="ATT1")
            ```
        """
        self.session.delete(f"{self.base_path}/{id}")

    def upload_and_attach_file_as_note(
        self,
        parent_id: str,
        file_data: IO,
        note_text: str = "",
        file_name: str = "",
        upload_key: str | None = None,
    ) -> Note:
        """Uploads a file and attaches it to a new note. A user can be tagged in the note_text string by using f-string and the User.to_note_mention() method.
        This allows for easy tagging and referencing of users within notes. example: f"Hello {tagged_user.to_note_mention()}!"

        Parameters
        ----------
        parent_id : str
            The ID of the parent entity onto which the note will be attached.
        file_data : IO
            The file data to upload.
        note_text : str, optional
            Any additional text to add to the note, by default ""
        file_name : str, optional
            The name of the file. Include a file extension to infer the content type;
            otherwise, the upload defaults to ``application/octet-stream``.
        upload_key : str | None, optional
            Override the storage key used when signing and uploading the file.
            Defaults to ``{parent_id}/{note_id}/{file_name}``.

        Returns
        -------
        Note
            The created note, with the uploaded file attached.

        !!! example
            ```python
            with open("results.csv", "rb") as fh:
                note = client.attachments.upload_and_attach_file_as_note(
                    parent_id="TASA1",
                    file_data=fh,
                    note_text="Attaching the raw results.",
                    file_name="results.csv",
                )
            ```
        """
        if not (upload_key or file_name):
            raise ValueError("A file name or upload key must be provided for attachment upload.")

        note_collection = self._get_note_collection()
        note = Note(
            parent_id=parent_id,
            note=note_text,
        )
        registered_note = note_collection.create(note=note)
        if upload_key:
            attachment_name = file_name or Path(upload_key).name
            upload_name = upload_key
        else:
            attachment_name = file_name
            upload_name = f"{parent_id}/{registered_note.id}/{file_name}"
        file_type = mimetypes.guess_type(attachment_name or upload_name)[0]
        if file_type is None:
            file_type = "application/octet-stream"
        file_collection = self._get_file_collection()

        file_collection.sign_and_upload_file(
            data=file_data,
            name=upload_name,
            namespace=FileNamespace.RESULT.value,
            content_type=file_type,
        )
        file_info = file_collection.get_by_name(
            name=upload_name, namespace=FileNamespace.RESULT.value
        )
        self.attach_file_to_note(
            note_id=registered_note.id,
            file_name=attachment_name,
            file_key=file_info.name,
        )

        return note_collection.get_by_id(id=registered_note.id)

    @validate_call
    def upload_and_attach_sds_to_inventory_item(
        self,
        *,
        inventory_id: InventoryId,
        file_sds: Path,
        revision_date: date,
        storage_class: str,
        un_number: str,
        jurisdiction_code: str = "US",
        language_code: str = "EN",
        hazard_statements: list[HazardStatement] | None = None,
        hazard_symbols: list[HazardSymbol] | None = None,
        wgk: str | None = None,
    ) -> Attachment:
        """Upload an SDS document and attach it to an inventory item.

        Parameters
        ----------
        inventory_id : str
            Id of Inventory Item to attach SDS to.
        file_sds : Path
            Local path to the SDS PDF to upload.
        revision_date : date
            Revision date for the SDS. (yyyy-mm-dd)
        un_number : str
            The UN number.
        storage_class : str
            The Storage Class number.
        jurisdiction_code : str, optional
            Jurisdiction code for the SDS (e.g. ``"US"``). Use
            ``get_jurisdiction_codes()`` to retrieve the full list of available codes.
        language_code : str, optional
            Language code for the SDS (e.g. ``"EN"``). Use
            ``get_language_codes()`` to retrieve the full list of available codes.
        hazard_statements : list[HazardStatement] | None, optional
            Collection of hazard statements.
        hazard_symbols : list[HazardSymbol] | None, optional
            Collection of hazard symbols.
        wgk : str | None, optional
            WGK classification metadata.

        Returns
        -------
        Attachment
            The created SDS attachment linked to the inventory item.

        !!! example
            ```python
            from datetime import date
            from pathlib import Path
            attachment = client.attachments.upload_and_attach_sds_to_inventory_item(
                inventory_id="INVA1",
                file_sds=Path("~/Downloads/acetone_sds.pdf"),
                revision_date=date(2024, 1, 1),
                storage_class="3",
                un_number="1090",
            )
            ```
        """

        sds_path = file_sds.expanduser()
        if not sds_path.is_file():
            raise FileNotFoundError(f"SDS file not found at '{sds_path}'")

        content_type = mimetypes.guess_type(sds_path.name)[0] or "application/pdf"

        extension = sds_path.suffix
        upload_id = self._generate_upload_id()
        file_key = f"{inventory_id}/SDS/{upload_id}{extension}"

        file_collection = self._get_file_collection()
        with sds_path.open("rb") as file_handle:
            file_collection.sign_and_upload_file(
                data=file_handle,
                name=file_key,
                namespace=FileNamespace.RESULT,
                content_type=content_type,
                category=FileCategory.SDS,
            )

        metadata: dict[str, MetadataItem] = {
            "jurisdictionCode": jurisdiction_code,
            "languageCode": language_code,
        }

        if revision_date is not None:
            metadata["revisionDate"] = revision_date.isoformat()

        if hazard_statements:
            metadata["hazardStatement"] = [
                statement.model_dump(by_alias=True, exclude_none=True)
                for statement in hazard_statements
            ]
        if hazard_symbols:
            metadata["Symbols"] = [
                symbol.model_dump(by_alias=True, exclude_none=True) for symbol in hazard_symbols
            ]

        if un_number is not None:
            metadata["unNumber"] = un_number
        if storage_class is not None:
            metadata["storageClass"] = storage_class
        if wgk is not None:
            metadata["wgk"] = wgk

        attachment = Attachment(
            parent_id=inventory_id,
            name=sds_path.name,
            key=file_key,
            namespace=FileNamespace.RESULT.value,
            category=AttachmentCategory.SDS,
            metadata=metadata,
            revision_date=revision_date,
        )
        return self.create(attachment=attachment)

    @staticmethod
    def _generate_upload_id() -> str:
        return str(uuid.uuid4())

    @validate_call
    def upload_and_attach_document_to_project(
        self,
        *,
        project_id: ProjectId,
        file_path: Path,
    ) -> Attachment:
        """Upload a file and attach it as a document to a project.

        Parameters
        ----------
        project_id : ProjectId
            The Albert ID of the project (e.g. ``PRO770``).
        file_path : Path
            Local path to the file to upload.

        Returns
        -------
        Attachment
            The created attachment record.

        !!! example
            ```python
            from pathlib import Path
            attachment = client.attachments.upload_and_attach_document_to_project(
                project_id="PRO770",
                file_path=Path("~/Downloads/report.pdf"),
            )
            ```
        """
        resolved_path = file_path.expanduser()
        if not resolved_path.is_file():
            raise FileNotFoundError(f"File not found at '{resolved_path}'")

        content_type = mimetypes.guess_type(resolved_path.name)[0] or "application/octet-stream"
        upload_id = self._generate_upload_id()
        extension = resolved_path.suffix
        file_key = f"{project_id}/documents/original/{upload_id}{extension}"

        file_collection = self._get_file_collection()
        with resolved_path.open("rb") as file_handle:
            file_collection.sign_and_upload_file(
                data=file_handle,
                name=file_key,
                namespace=FileNamespace.RESULT,
                content_type=content_type,
            )

        attachment = Attachment(
            parent_id=project_id,
            name=resolved_path.name,
            key=file_key,
            namespace=FileNamespace.RESULT.value,
            category=AttachmentCategory.OTHER,
        )
        return self.create(attachment=attachment)
