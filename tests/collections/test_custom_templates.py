from collections.abc import Iterable

from albert.albert import Albert
from albert.resources.custom_templates import CustomTemplate, _CustomTemplateDataUnion


def _list_asserts(list_iterator: Iterable[CustomTemplate]):
    # found = False
    for i, u in enumerate(list_iterator):
        if i == 50:
            break
        assert isinstance(u, CustomTemplate)
        # found = True
        if u.data is not None:
            assert isinstance(u.data, _CustomTemplateDataUnion)
    # assert found
    # TODO: No custom templates loaded to test yet  :(


def test_basics(client: Albert):
    list_response = client.templates.list()
    _list_asserts(list_response)
