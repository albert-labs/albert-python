from albert.resources.parameter_groups import (
    ParameterGroup,
    ParameterGroupSearchItem,
)


def test_parameter_group_search_item_sanitizes_empty_entity_link_metadata():
    """Some tenants have parameter-group metadata whose entity-link fields were
    cleared server-side to `[{}]` instead of `[]`, which fails `MetadataItem`
    validation.
    """
    raw = {
        "albertId": "PRG23111",
        "name": "sdfgfdgd",
        "metadata": {
            "AdvCTDSTPT_1": [{}],
            "AdvPGLSPTINV_2": [{}],
            "ADVNUMPTPG_1": 23,
            "ADVNUMPTPG_2": 445,
        },
    }
    item = ParameterGroupSearchItem(**raw)
    assert item.metadata["AdvCTDSTPT_1"] == []
    assert item.metadata["AdvPGLSPTINV_2"] == []
    assert item.metadata["ADVNUMPTPG_1"] == 23
    assert item.metadata["ADVNUMPTPG_2"] == 445


def test_parameter_group_sanitizes_empty_entity_link_metadata():
    """Same defect as above but against the hydrated ParameterGroup model."""
    raw = {
        "albertId": "PRG23111",
        "name": "sdfgfdgd",
        "class": "shared",
        "Metadata": {
            "AdvCTDSTPT_1": [{}],
            "bareEmptyLink": {},
            "ADVNUMPTPG_1": 23,
        },
    }
    pg = ParameterGroup(**raw)
    assert pg.metadata["AdvCTDSTPT_1"] == []
    assert "bareEmptyLink" not in pg.metadata
    assert pg.metadata["ADVNUMPTPG_1"] == 23
