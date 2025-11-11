from albert import Albert
from albert.resources.hazards import HazardStatement, HazardSymbol


def assert_valid_items(items: list, model: HazardSymbol | HazardStatement):
    assert items, "Expected at least one result"
    for item in items[:10]:
        assert isinstance(item, model)


def test_get_hazard_symbols(client: Albert):
    symbols = client.hazards.get_symbols()
    assert_valid_items(symbols, HazardSymbol)


def test_get_hazard_statements(client: Albert):
    statements = client.hazards.get_statements()
    assert_valid_items(statements, HazardStatement)
