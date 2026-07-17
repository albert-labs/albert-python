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

### Where the HTML file lives

You never upload to S3 yourself. `create(template_html=...)` sends the HTML through the template API, which stores it for your tenant under the `template_file` name; that name is the file's identity. There is no URL at create time: when a label is printed, the platform resolves the template record's `template_file` into the stored file's URL (returned as `payload.template.body`) and the renderer fetches it server-side.

Two consequences of the name-is-identity model:

- Uploading a file with the same `template_file` name replaces the stored file for the whole tenant, so pick distinct names unless replacement is what you want.
- `update()` can repoint a template record to a different `template_file` name, but the only way to upload file content is `create()`. To revise a template's HTML, create a new template with the corrected file (or re-upload under the same file name and delete the extra record).

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

A template file is a complete, ordinary HTML document with placeholders where the label's data goes. The placeholder syntax is [Mustache](https://mustache.github.io/mustache.5.html): `{{info.inventoryName}}` inserts a value, `{{#info.Symbols}}...{{/info.Symbols}}` repeats a block for each item in a list, and `{{{info.lotNumber}}}` (triple braces) inserts a value without HTML escaping. That is all the syntax there is; if you can write HTML and CSS, you can write a label template. At print time the placeholders are filled in and the page is printed to PDF by headless Chrome.

The placeholder names are not arbitrary: they are the fields of the print payload assembled for your template's `type`. The full list per type is in [Data available to each template type](#data-available-to-each-template-type) below, and `get_print_payload(type=...)` returns the exact data (`payload.data["labels"]`) your template will be rendered with.

The general shape is:

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

The metadata block carries two kinds of keys: PDF page options consumed by the renderer, and label-assembly settings consumed while gathering the data. The same keys can also be set on the template record's `metadata` when creating via the SDK; the file block wins where both define a key.

**Page options** (the renderer reads exactly these; anything else is ignored — see `PDFOptions`):

| Key | Purpose |
| --- | --- |
| `width`, `height` | Page size as CSS lengths (e.g. `"3in"`, `"1in"`). Both must be set to apply. |
| `format` | Named paper size (e.g. `"A4"`, `"Letter"`) as an alternative to `width`/`height`. |
| `margin` | Object with `top`/`bottom`/`left`/`right`. |
| `landscape` | Render in landscape orientation when `true`. |
| `renderBackgroundImage` | Print CSS background colors and images when `true`. |
| `hideHeaderFromFirstPage` | Skip the header on page 1 (title-page pattern) when `true`. |

**Label-assembly settings**:

| Key | Purpose |
| --- | --- |
| `hasBlackPictos` | Use the black (no-line) pictogram set. |
| `useGhsOfficialPictos` | Use official GHS pictogram images. |
| `numberOfPictos` | Cap how many hazard pictograms are passed to the template. |
| `header`, `footer` | File names of separate header/footer HTML files. |
| `languageCode` | Language for regulatory precautionary phrases (default `EN`). |
| `templateId` | Informational name for the file. |

## Headers, footers, and page numbers

For multi-page outputs (reports, certificates), a template can have separate header and footer HTML files. Reference them in the metadata block (`"header"`, `"footer"`) or upload them via `create(header_html=..., footer_html=...)`, with their file names in the template record's `metadata`.

Header and footer templates repeat on every page and support special classes that the renderer fills in:

```html
<div style="font-size: 8px; width: 100%; text-align: right; padding-right: 1cm;">
  Page <span class="pageNumber"></span> of <span class="totalPages"></span>
</div>
```

Available classes: `pageNumber`, `totalPages`, `date`, `title`. Set `hideHeaderFromFirstPage: true` in the options to keep the first page clean while headers appear on subsequent pages. Size the header/footer with inline styles and leave room for them via the page `margin`.

## Data available to each template type

Each entry in `{{#labels}}` exposes its fields under `info` (except `propertytaskreport`, noted below). All types also receive `{{info.currentUser.name}}` and `{{info.currentUser.email}}` (the printing user). Whatever the tables below say, `get_print_payload(type=...)` is always the ground truth for what a given template receives.

### `inventory` (Lot barcode labels)

Print with `inventory_lot_number_id` (one or more Lot IDs).

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
| `{{info.rsnNumber}}`, `{{info.idh}}` | Values from inventory metadata where present. |
| `{{info.logo}}` | Tenant logo image URL. |
| `{{#info.Symbols}}` | Loop of hazard pictogram image URLs. |
| `{{info.AdditionalInfo.InventoryInfo...}}` | The full Inventory object, including `Metadata.<customField>`. |
| `{{info.AdditionalInfo.LotInfo...}}` | The full Lot object (e.g. `StorageLocation.name`, `manufacturerLotNumber`). |
| `{{info.AdditionalInfo.RegulatoryInfo...}}` | Regulatory data for the item (hazard statements, precautionary phrases). |

### `batch` (Product/Formula lot labels)

Print with `albert_id` (the formula Inventory ID) and `task_id` (the batch task). One entry total.

| Field | Contents |
| --- | --- |
| `{{info.albertId}}` / `{{info.formulaID}}` | Formula Inventory ID (prefix stripped). |
| `{{info.formulaName}}` | Formula name. |
| `{{info.lotId}}` | Batch lot display ID (e.g. `B123-4`). |
| `{{info.lotNumber}}` | Batch lot number prefix as **text** (no barcode image for this type). |
| `{{info.taskID}}`, `{{info.taskName}}` | Batch task ID and name. |
| `{{info.batchWeight}}` | Batch size. |
| `{{info.batchStartDate}}` | Task start date. |
| `{{info.batchLocation.name}}` | Task location. |
| `{{info.taskOwner}}` | Assigned user name. |
| `{{info.taskTags}}` | Task tags. |
| `{{info.Project.id}}`, `{{info.Project.name}}`, `{{info.Project.Technology}}` | Parent project details. |
| `{{#info.hasQcTasks}}` / `{{#info.QCResultsTable}}` | QC task rows, each with `info.taskId`, `info.barcodeId`, `info.property`, `info.target`, `info.qcResult`, `info.qcResultStatus`, `info.ParameterGroups`. |
| `{{info.Created...}}`, `{{info.Updated...}}` | Template audit info. |
| `{{info.logo}}`, `{{info.backgroundImageUrl}}` | Tenant logo and background image URLs. |

### `property` (Property task interval labels)

Print with `task_id` and `albert_id`; optionally `lot_id` and `block_id`. One entry per inventory x block x interval, so these templates are usually printed as one small label per page.

| Field | Contents |
| --- | --- |
| `{{{info.lotNumber}}}` | **Barcode image URL** encoding task-inventory-block-interval. |
| `{{{info.lotNumberQrCode}}}` | **QR code image** of the same code, as a `data:` URI. |
| `{{info.intervalId}}` | Human-readable interval name. |
| `{{info.blockId}}`, `{{info.intervalRow}}` | Block and interval row IDs. |
| `{{info.taskID}}`, `{{info.taskName}}` | Property task ID and name. |
| `{{info.albertId}}`, `{{info.inventoryName}}`, `{{info.alias}}`, `{{info.lotId}}` | The inventory/lot the label is for. |
| `{{info.propertyName}}` / `{{info.Datatemplate}}` | The data template (property) being measured. |
| `{{info.startDate}}`, `{{info.dueDate}}`, `{{info.priority}}`, `{{info.state}}`, `{{info.status}}`, `{{info.result}}`, `{{info.target}}` | Task fields. |
| `{{info.AssignedTo.name}}`, `{{info.Location...}}`, `{{info.Tags}}`, `{{info.Workflow...}}` | Task assignment details. |
| `{{info.ParameterGroups...}}`, `{{info.Notes}}`, `{{info.Tasks}}`, `{{info.History}}` | Workflow parameter groups, task notes, related lot tasks, task history. |
| `{{info.Created.date}}` | Task creation date (formatted). |
| `{{#info.Symbols}}` | Loop of hazard pictogram image URLs. |
| `{{info.formulaIngredient}}` | Unpacked formula ingredients, for formula inventories. |
| `{{info.AdditionalInfo...}}` | `InventoryInfo`, `LotInfo`, `projectInfo`, and `TaskMetadata` objects. |
| `{{info.logo}}` | Tenant logo image URL. |

Data template names honor the `x-alb-language` request header for localization.

### `propertytaskreport` (Property task reports)

Print with `task_id` and `albert_id`. One entry, and uniquely its fields are **top-level** (no `info` wrapper): `{{task...}}` (the full task), `{{taskHistory}}`, `{{propertyDataResult}}` (processed property data by block/interval), `{{wflPGData}}` (workflow parameter groups), `{{projectDetails...}}`, and `{{taskNotes}}`.

### `batchtemplate` (Batch task documents, e.g. CoA)

Print with `task_id`. One entry.

| Field | Contents |
| --- | --- |
| `{{info.overview.taskId}}`, `{{info.overview.taskName}}` | Batch task ID and name. |
| `{{{info.overview.taskIdBarcode}}}` | **Barcode image** of the task ID, as a `data:` URI. |
| `{{#info.overview.Product}}` | Loop of produced formulas: `id`, `name`, `lotNumber`, `barcodeId`. |
| `{{info.overview.Created...}}`, `{{info.overview.AssignedTo...}}` | Task audit and assignee. |
| `{{#info.tableJson}}` | Batch usage tables (raw materials and amounts), grouped per `numberOfProducts` from the metadata block. |
| `{{info.workflows...}}` | The task's final workflow, including parameter groups. |
| `{{info.projectDetails...}}` | Parent project, including `Metadata.<customField>`. |
| `{{info.AdditionalInfo.TaskInfo...}}` | The full task object, including `Metadata.<customField>`. |
| `{{info.AdditionalInfo.TaskNotes}}` | Task notes. |

This type pairs naturally with `{{manualFields.X}}` placeholders and a metadata `schema` block for operator-entered values (see below).

### `generaltasklabel` (General task labels)

Print with `task_id`. One entry whose `info` is the **full task object**, enriched with:

| Field | Contents |
| --- | --- |
| `{{info.displayId}}` | Task ID with the prefix stripped. |
| `{{info.name}}`, `{{info.status}}`, and all other task fields | The task record itself. |
| `{{info.ProjectInfo...}}` | The full parent project. |
| `{{#info.Inventories}}` | Loop of task inventories, each with `displayId`, `inventoryInfo` (full inventory record, `Symbols` resolved to pictogram URLs) and `lotInfo` (full lot record, plus `RecentTransferDate`). |

### `batchlabel` and `formulareport` (direct generation)

These two types skip the print-payload step entirely; the platform assembles the data and renders the PDF in one call, returning a finished URL:

```python
url = client.label_templates.get_batch_label_url(task_id="TAS1234")
url = client.label_templates.get_formula_report_url(formula_id="INVA1234-001", template_id="TMP123")
```

The GHS batch label (`batchlabel`) is rendered by the platform's document generator with computed hazard data (signal word, hazard and precautionary statements, pictograms); its template is not a tenant label template file. The formula report uses a `formulareport` tenant template with internally assembled composition and results data.

## Mustache patterns that matter

**Use triple braces for image sources.** Barcode URLs and QR `data:` URIs contain characters that double braces would HTML-escape into broken links:

```html
<img src="{{{info.lotNumber}}}" width="100" height="40">
<img src="{{{info.lotNumberQrCode}}}" width="90" height="90">
```

The barcode image itself is a fixed-format Code 128 PNG with the human-readable text always included; style it by sizing, rotating, or cropping the `<img>` in CSS (only the text size is tunable server-side, via the `generate_barcode` endpoint's `text_size`).

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
