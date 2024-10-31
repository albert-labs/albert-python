import json

import requests

from albert import Albert
from albert.resources.files import FileNamespace


def test_file_round_trip(client: Albert):
    file_data = {"hello": "world"}
    file_name = "breakthrough/test/test.json"

    # First: Put a new file at the key
    client.files.sign_and_upload_file(
        data=json.dumps(file_data).encode(),
        name=file_name,
        namespace=FileNamespace.BREAKTHROUGH,
        content_type="application/json",
    )

    # Second: Retrieve the file info
    file_info = client.files.get_by_name(name=file_name, namespace=FileNamespace.BREAKTHROUGH)
    assert file_info.name == file_name
    assert file_info.content_type == "application/json"

    # Third: Get a download URL for the file
    download_url = client.files.get_signed_download_url(
        name=file_name,
        namespace=FileNamespace.BREAKTHROUGH,
    )

    # Last: Download the file and compare the data
    response = requests.get(download_url)
    assert response.json() == file_data
