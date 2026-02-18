# Projects

Projects in Albert are a way to organize and plan out work. They help promote digital collaboration between teams while also protecting Intellectual Property (IP).

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

## Search projects via metadata/custom fields

!!! example "Search projects using metadata filters"
    ```python
    from albert import Albert

    client = Albert.from_client_credentials()

    projects = client.projects.search(
        application=["Albert"],
        metadata_filters={
            "project_description": ["This project is about testing the SDK."],
            "adpNumber": ["1234", "5678"],
            "adpType": {"name": ["test-sdk"]},
        },
    )
    # adpType is a list-type custom field.
    # adpNumber is a string-type custom field.

    for project in projects:
        print(project)
    ```
