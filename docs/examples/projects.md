# Projects

Projects in Albert are a way to organize information and plan out work. They are designed to promote digital collaboration between teams while also protecting Intellectual Property (IP).

## Upload a project document

!!! example "Upload a document to a project"
    ```python
    from albert import Albert

    client = Albert.from_client_credentials()

    with open("path/to/document.pdf", "rb") as file:
        document = client.projects.upload_document(
            project_id="PRO123",
            file_data=file,
            file_name="document.pdf",
        )
    print(document)
    ```
