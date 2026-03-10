import mimetypes
import uuid
from datetime import date
from pathlib import Path
from typing import IO, Any

from pydantic import ValidationError, validate_call

from albert.collections.base import BaseCollection
from albert.collections.files import FileCollection
from albert.collections.notes import NotesCollection
from albert.core.base import BaseAlbertModel
from albert.core.shared.identifiers import AttachmentId, DataColumnId, InventoryId, ProjectId
from albert.core.shared.models.patch import PatchDatum, PatchOperation, PatchPayload
from albert.core.shared.types import MetadataItem
from albert.resources.attachments import Attachment, AttachmentCategory, AttachmentMetadata
from albert.resources.files import FileCategory, FileNamespace
from albert.resources.hazards import HazardStatement, HazardSymbol
from albert.resources.notes import Note


class AttachmentCollection(BaseCollection):
    """AttachmentCollection is a collection class for managing Attachment entities in the Albert platform."""

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
        """Retrieves an attachment by its ID.

        Parameters
        ----------
        id : AttachmentId
            The ID of the attachment to retrieve.

        Returns
        -------
        Attachment
            The Attachment object corresponding to the provided ID.
        """
        response = self.session.get(url=f"{self.base_path}/{id}")
        return Attachment(**response.json())

    @validate_call
    def create(self, *, attachment: Attachment) -> Attachment:
        """Create a new attachment.

        Parameters
        ----------
        attachment : Attachment
            The attachment to create.

        Returns
        -------
        Attachment
            The created attachment.
        """
        payload = attachment.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = self.session.post(self.base_path, json=payload)
        return Attachment(**response.json())

    @validate_call
    def update(self, *, attachment: Attachment) -> Attachment:
        """Update an attachment by diffing the current server state.

        Parameters
        ----------
        attachment : Attachment
            Attachment object containing the desired final state. The attachment must include ``id``.

        Returns
        -------
        Attachment
            The updated attachment returned by the API.
        """
        if attachment.id is None:
            raise ValueError("Attachment ID is required for update.")

        existing_attachment = self.get_by_id(id=attachment.id)
        payload = self._generate_attachment_patch_payload(
            existing=existing_attachment, updated=attachment
        )
        if len(payload.data) == 0:
            return existing_attachment

        self.session.patch(
            f"{self.base_path}/{attachment.id}",
            json=payload.model_dump(by_alias=True, mode="json"),
        )
        return self.get_by_id(id=attachment.id)

    @staticmethod
    def _serialize_patch_value(value: Any) -> Any:
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, BaseAlbertModel):
            return value.model_dump(by_alias=True, mode="json", exclude_none=True)
        return value

    @staticmethod
    def _normalize_metadata_item(value: Any) -> Any:
        value = AttachmentCollection._serialize_patch_value(value)
        if isinstance(value, dict):
            if value.get("id") is not None:
                return value["id"]
            if value.get("name") is not None:
                return value["name"]
        return value

    @staticmethod
    def _get_metadata_dict(*, attachment: Attachment) -> dict[str, Any]:
        metadata = attachment.metadata
        if metadata is None:
            return {}
        if isinstance(metadata, BaseAlbertModel):
            return metadata.model_dump(by_alias=True, mode="json", exclude_none=True)
        metadata_dict = dict(metadata)
        try:
            normalized = AttachmentMetadata.model_validate(metadata_dict)
            return normalized.model_dump(by_alias=True, mode="json", exclude_none=True)
        except ValidationError:
            return metadata_dict

    def _generate_attachment_patch_payload(
        self, *, existing: Attachment, updated: Attachment
    ) -> PatchPayload:
        patch_data: list[PatchDatum] = list(
            self._generate_patch_payload(
                existing=existing,
                updated=updated,
                generate_metadata_diff=False,
            ).data
        )

        existing_metadata = self._get_metadata_dict(attachment=existing)
        updated_metadata = self._get_metadata_dict(attachment=updated)
        metadata_keys = set(existing_metadata) | set(updated_metadata)
        for key in metadata_keys:
            if key not in self._updatable_metadata_attributes:
                continue

            old_value = existing_metadata.get(key)
            new_value = updated_metadata.get(key)
            old_is_list = isinstance(old_value, list)
            new_is_list = isinstance(new_value, list)
            if old_is_list or new_is_list:
                old_items = old_value if old_is_list else []
                new_items = new_value if new_is_list else []
                old_norm = [self._normalize_metadata_item(value=x) for x in old_items]
                new_norm = [self._normalize_metadata_item(value=x) for x in new_items]

                for old_item in old_norm:
                    if old_item not in new_norm:
                        old_patch_value = [{"id": old_item}] if key == "Symbols" else old_item
                        patch_data.append(
                            PatchDatum(
                                attribute=key,
                                operation=PatchOperation.DELETE,
                                old_value=old_patch_value,
                            )
                        )
                for new_item in new_norm:
                    if new_item not in old_norm:
                        new_patch_value = [{"id": new_item}] if key == "Symbols" else new_item
                        patch_data.append(
                            PatchDatum(
                                attribute=key,
                                operation=PatchOperation.ADD,
                                new_value=new_patch_value,
                            )
                        )
                continue

            old_norm = self._normalize_metadata_item(value=old_value)
            new_norm = self._normalize_metadata_item(value=new_value)
            if old_norm is None and new_norm is not None:
                patch_data.append(
                    PatchDatum(
                        attribute=key,
                        operation=PatchOperation.ADD,
                        new_value=new_norm,
                    )
                )
            elif old_norm is not None and new_norm is None:
                patch_data.append(
                    PatchDatum(
                        attribute=key,
                        operation=PatchOperation.DELETE,
                        old_value=old_norm,
                    )
                )
            elif old_norm is not None and new_norm != old_norm:
                patch_data.append(
                    PatchDatum(
                        attribute=key,
                        operation=PatchOperation.UPDATE,
                        old_value=old_norm,
                        new_value=new_norm,
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
            Parent IDs of the objects to which the attachments are linked.

        Returns
        -------
        dict[str, list[Attachment]]
            A dictionary mapping parent IDs to lists of Attachment objects associated with each parent ID.
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
            The type of file, by default FileCategory.OTHER

        Returns
        -------
        Attachment
            The related attachment object.
        """
        attachment = Attachment(
            parent_id=note_id, name=file_name, key=file_key, namespace="result", category=category
        )
        return self.create(attachment=attachment)

    @validate_call
    def delete(self, *, id: AttachmentId) -> None:
        """Deletes an attachment by ID.

        Parameters
        ----------
        id : str
            The ID of the attachment to delete.

        Returns
        -------
        None
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
            The created note.
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
        jurisdiction_code : str | None, optional
            Jurisdiction code associated with the SDS (e.g. ``US``).
        language_code : str, optional
            Language code for the SDS (e.g. ``EN``).
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
