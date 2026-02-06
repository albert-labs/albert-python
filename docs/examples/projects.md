# Projects

## Upload a project document

!!! example "Upload a document to a project"
    ```python
    from albert import Albert

    client = Albert.from_client_credentials()

    with open("path/to/document.pdf", "rb") as file:
        attachment = client.attachments.upload_document(
            project_id="PRO123",
            file_data=file,
            file_name="document.pdf",
        )
    print(attachment)
    ```
