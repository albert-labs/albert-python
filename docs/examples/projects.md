# Projects

## Upload a project document

!!! example "Upload a document to a project"
    ```python
    from albert import Albert

    client = Albert.from_client_credentials()

    attachment = client.attachments.upload_and_attach_document_to_project(
        project_id="PRO123",
        file_path="path/to/document.pdf",
    )
    print(attachment)
    ```
