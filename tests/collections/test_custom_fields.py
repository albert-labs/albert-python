from albert.albert import Albert
from albert.resources.custom_fields import CustomField


def test_update(client: Albert, static_custom_fields: list[CustomField]):
    # Custom fields are preloaded and fixed, so we can't modify them without affecting other test runs
    # Just set hidden = True to test the update call, even though the value may not be changing
    cf = static_custom_fields[0].model_copy()
    cf.hidden = True
    cf = client.custom_fields.update(custom_field=cf)
    assert cf.hidden
