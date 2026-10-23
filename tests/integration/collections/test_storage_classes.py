from albert import Albert
from albert.resources.storage_classes import StorageClass, StorageCompatibilityMatrix


def test_storage_classes_get_all(client: Albert):
    storage_classes = client.storage_classes.get_all()

    assert isinstance(storage_classes, list)
    assert storage_classes, "Expected at least one storage class entry"

    for entry in storage_classes[:10]:
        assert isinstance(entry, StorageClass)
        if entry.storage_compatibility is not None:
            assert isinstance(entry.storage_compatibility, StorageCompatibilityMatrix)
