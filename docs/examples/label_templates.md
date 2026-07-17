# Label Templates

Label templates drive the printable outputs in Albert, such as inventory lot barcode labels, batch task labels, and formula reports. A label template is a Mustache HTML file stored for your tenant, plus a template record that names it, types it, and holds its page options.

This page covers the end-to-end SDK workflow and, most importantly, the rules for authoring the template HTML file itself.

## End-to-end workflow

!!! example "Create a template and print a Lot label"
    ```python
    from pathlib import Path

    from albert import Albert
    from albert.resources.label_templates import LabelTemplate, LabelTemplateType

    client = Albert.from_client_credentials()

    # 1) Create the template, uploading its HTML file
    template = LabelTemplate(
        name="3x1 Inventory Label",
        type=LabelTemplateType.INVENTORY,
        template_file="3x1-inventory-label.html",
        metadata={
            "width": "3in",
            "height": "1in",
            "margin": {"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"},
        },
    )
    created = client.label_templates.create(
        label_template=template,
        template_html=Path("3x1-inventory-label.html").read_text(),
    )

    # 2) Generate a label PDF for a Lot
    url = client.label_templates.generate_label_pdf(
        inventory_lot_number_id="LOTB1234",
        template_id=created.id,
    )
    # url is a short-lived link to the rendered PDF
    ```

To inspect what data a template will receive (or to render manually), use `get_print_payload`:

!!! example "Inspect the render payload"
    ```python
    payload = client.label_templates.get_print_payload(
        inventory_lot_number_id="LOTB1234",
        template_id=created.id,
    )
    payload.template.body  # URL of the stored Mustache HTML file
    payload.data["labels"]  # one entry per printed entity
    ```

## Anatomy of a template file

A template file is a complete HTML document. It is rendered with [Mustache](https://mustache.github.io/mustache.5.html) and printed to PDF by headless Chrome. The general shape is:

```html
<html>
<head>
  <meta charset="UTF-8">
  <!-- DO NOT MODIFY the below commented line, API (template/print) is consuming it -->
  <!--metadata:{
    "width": "3in",
    "height": "1in",
    "margin": {"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"},
    "renderBackgroundImage": true
  }-->
  <style>
    /* Inline CSS. Fixed sizing is typical: 1in = 96px. */
    body { width: 100%; overflow: hidden; }
  </style>
</head>
<body>
  {{#labels}}
  <!-- One block per printed entity -->
  <div class="label-container">
    ...
  </div>
  {{/labels}}
</body>
</html>
```

Key rules:

- **Wrap the body in `{{#labels}} ... {{/labels}}`.** The render data is `{"labels": [...]}` with one entry per printed entity, and each entry's fields live under `info`.
- **The `<!--metadata:{...}-->` comment must contain valid JSON.** It is parsed out of the file and merged over the template record's `metadata`; the merged object supplies the PDF page options (`width`, `height`, `margin`, and so on).
- **The page renders in headless Chrome and waits for network idle**, so externally hosted fonts, stylesheets, and images load before printing. Inline `<script>` tags also run before printing, so DOM post-processing is supported.
- **Size the page explicitly.** Set `width`/`height` in the metadata (or template record `metadata`) and size your containers to match, with `overflow: hidden` to prevent spill. When printing multiple entities in one PDF, use `page-break-before: always` / `page-break-after: always` on the per-label container.

## The metadata block

Recognized keys observed across production templates:

| Key | Purpose |
| --- | --- |
| `width`, `height` | Page size (e.g. `"3in"`, `"1in"`). |
| `margin` | Object with `top`/`bottom`/`left`/`right`. |
| `renderBackgroundImage` | Print CSS backgrounds when `true`. |
| `hasBlackPictos` | Use the black (no-line) pictogram set. |
| `useGhsOfficialPictos` | Use official GHS pictogram images. |
| `numberOfPictos` | Cap how many hazard pictograms are passed to the template. |
| `header`, `footer` | File names of separate header/footer HTML files. |
| `templateId` | Informational name for the file. |

The same keys can also be set on the template record's `metadata` when creating via the SDK; the file block wins where both define a key.

## Data available to inventory labels

Each entry in `{{#labels}}` exposes these fields under `info` for `type=inventory`:

| Field | Contents |
| --- | --- |
| `{{info.albertId}}` | The parent Inventory ID. |
| `{{info.inventoryName}}` | Inventory item name. |
| `{{info.alias}}` | Inventory alias. |
| `{{{info.lotNumber}}}` | **Barcode image URL** for the lot. Use inside `<img src="...">`. |
| `{{{info.lotNumberQrCode}}}` | **QR code image** as a `data:` URI. Use inside `<img src="...">`. |
| `{{info.vendorLotNumber}}` | Manufacturer lot number. |
| `{{info.Supplier}}` / `{{info.manufacturer}}` | Supplier/manufacturer company name. |
| `{{info.owner}}` | Lot owner name. |
| `{{info.lotCreationDate}}` | Lot creation date. |
| `{{info.expirationDate}}` | Lot expiration date. |
| `{{info.locationAddress}}` | Location address. |
| `{{info.sublocation}}` | Location and storage location names combined. |
| `{{info.inventoryCategory}}` | Parent category (e.g. RawMaterials). |
| `{{info.logo}}` | Tenant logo image URL. |
| `{{#info.Symbols}}` | Loop of hazard pictogram image URLs. |
| `{{info.AdditionalInfo.InventoryInfo...}}` | The full Inventory object, including `Metadata.<customField>`. |
| `{{info.AdditionalInfo.LotInfo...}}` | The full Lot object (e.g. `StorageLocation.name`, `manufacturerLotNumber`). |
| `{{info.AdditionalInfo.RegulatoryInfo...}}` | Regulatory data for the item. |

Other template types receive different fields (for example, batch and property task labels expose `info.taskId`, `info.taskName`, and loop pictograms via `{{#info.pictograms}}`). Use `get_print_payload` with the matching `type` to see exactly what a template will receive.

## Mustache patterns that matter

**Use triple braces for image sources.** Barcode URLs and QR `data:` URIs contain characters that double braces would HTML-escape into broken links:

```html
<img src="{{{info.lotNumber}}}" width="100" height="40">
<img src="{{{info.lotNumberQrCode}}}" width="90" height="90">
```

**Loop arrays with sections.** Inside a loop, `{{.}}` is the current item:

```html
{{#info.Symbols}}
  <img src="{{.}}" width="15" height="15">
{{/info.Symbols}}
```

**Use inverted sections for fallbacks.** For example, show the storage location, falling back to the location:

```html
{{#info.AdditionalInfo.LotInfo.StorageLocation.name}}
  {{info.AdditionalInfo.LotInfo.StorageLocation.name}}
{{/info.AdditionalInfo.LotInfo.StorageLocation.name}}
{{^info.AdditionalInfo.LotInfo.StorageLocation.name}}
  {{info.AdditionalInfo.LotInfo.Location.name}}
{{/info.AdditionalInfo.LotInfo.StorageLocation.name}}
```

**Reach custom fields through `AdditionalInfo`.** Tenant custom fields on the Inventory are available at `{{info.AdditionalInfo.InventoryInfo.Metadata.<fieldName>}}`.

**Manual fields.** Placeholders of the form `{{manualFields.<Name>}}` are detected in the file and surfaced so the user is prompted for values before printing. They are returned in `LabelPrintPayload.manual_fields`.

## Complete example: 3x1in inventory lot label

A functional starting point (plain black-and-white, barcode plus QR plus pictograms):

```html
<html>
<head>
  <meta charset="UTF-8">
  <!-- DO NOT MODIFY the below commented line, API (template/print) is consuming it -->
  <!--metadata:{
    "width": "3in",
    "height": "1in",
    "margin": {"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"},
    "renderBackgroundImage": true
  }-->
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: Arial, sans-serif; overflow: hidden; }
    .label-container {
      display: grid;
      grid-template-columns: 180px 108px;
      width: 288px;   /* 3in */
      height: 96px;   /* 1in */
      overflow: hidden;
      padding: 4px;
      page-break-after: always;
    }
    .name { font-size: 10px; font-weight: 700; }
    .field { font-size: 8px; }
    .field b { font-weight: 700; }
    .pictos img { width: 14px; height: 14px; }
  </style>
</head>
<body>
{{#labels}}
  <div class="label-container">
    <div>
      <div class="name">{{info.inventoryName}}</div>
      <div class="field"><b>ID:</b> {{info.albertId}}</div>
      <div class="field"><b>Mfr Lot #:</b> {{info.vendorLotNumber}}</div>
      <div class="field"><b>Location:</b> {{info.sublocation}}</div>
      <div class="field"><b>Exp:</b> {{info.expirationDate}}</div>
      <div class="pictos">
        {{#info.Symbols}}<img src="{{.}}">{{/info.Symbols}}
      </div>
    </div>
    <div>
      <img src="{{{info.lotNumber}}}" width="100" height="40">
      <img src="{{{info.lotNumberQrCode}}}" width="45" height="45">
    </div>
  </div>
{{/labels}}
</body>
</html>
```
