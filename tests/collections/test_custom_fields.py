from albert.albert import Albert
from albert.resources.custom_fields import CustomField


def test_update(client: Albert, seeded_custom_fields):
    # get field
    cf = seeded_custom_fields[0]
    # modify locally
    cf.hidden = True
    # update
    cf_updated = client.custom_fields.update(custom_field=cf)
    assert isinstance(cf_updated, CustomField)
    assert cf_updated.hidden == True
    # modify locally
    cf_updated.hidden = False
    # update
    cf = client.custom_fields.update(custom_field=cf_updated)
    assert isinstance(cf, CustomField)
    assert cf.hidden == False
