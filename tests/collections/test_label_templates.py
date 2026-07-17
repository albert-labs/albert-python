from albert.client import Albert
from albert.resources.label_templates import (
    LabelPrintPayload,
    LabelTemplate,
    LabelTemplateType,
)
from albert.resources.lots import Lot


def test_label_template_get_by_id(client: Albert, seeded_label_templates: list[LabelTemplate]):
    """Test get_by_id returns a fully populated LabelTemplate."""
    seeded = seeded_label_templates[0]
    fetched = client.label_templates.get_by_id(id=seeded.id)
    assert isinstance(fetched, LabelTemplate)
    assert fetched.id == seeded.id
    assert fetched.name == seeded.name
    assert fetched.type == LabelTemplateType.INVENTORY
    assert fetched.template_file == seeded.template_file


def test_label_template_get_all(client: Albert, seeded_label_templates: list[LabelTemplate]):
    """Test get_all returns matching LabelTemplate items."""
    seeded = seeded_label_templates[0]
    results = list(client.label_templates.get_all(type=LabelTemplateType.INVENTORY, max_items=50))
    assert results
    for template in results:
        assert isinstance(template, LabelTemplate)
        assert template.type == LabelTemplateType.INVENTORY
    assert any(template.id == seeded.id for template in results)


def test_label_template_update(client: Albert, seeded_label_templates: list[LabelTemplate]):
    """Test update changes the name of a label template."""
    seeded = seeded_label_templates[0]
    template = client.label_templates.get_by_id(id=seeded.id)
    updated_name = f"{template.name}-updated"
    template.name = updated_name
    updated = client.label_templates.update(label_template=template)
    assert updated.name == updated_name

    # Restore the original name so other tests see consistent state
    updated.name = seeded.name
    restored = client.label_templates.update(label_template=updated)
    assert restored.name == seeded.name


def test_label_template_get_print_payload(
    client: Albert,
    seeded_label_templates: list[LabelTemplate],
    seeded_lots: list[Lot],
):
    """Test get_print_payload assembles the label render payload for a Lot."""
    seeded_template = seeded_label_templates[0]
    seeded_lot = seeded_lots[0]

    payload = client.label_templates.get_print_payload(
        inventory_lot_number_id=seeded_lot.id,
        template_id=seeded_template.id,
    )
    assert isinstance(payload, LabelPrintPayload)
    assert payload.template.body.endswith(seeded_template.template_file)
    assert payload.s3_storage.bucket
    assert payload.s3_storage.key
    assert payload.data.get("labels")


def test_label_template_generate_label_pdf(
    client: Albert,
    seeded_label_templates: list[LabelTemplate],
    seeded_lots: list[Lot],
):
    """Test generate_label_pdf returns a download URL for the rendered label."""
    seeded_template = seeded_label_templates[0]
    seeded_lot = seeded_lots[0]

    url = client.label_templates.generate_label_pdf(
        inventory_lot_number_id=seeded_lot.id,
        template_id=seeded_template.id,
    )
    assert isinstance(url, str)
    assert url.startswith("http")
