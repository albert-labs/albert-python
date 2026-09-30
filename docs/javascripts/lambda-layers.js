// Renders the public Lambda layer catalog into #lambda-layer-catalog on the AWS Lambda
// layer page. The catalog is published outside the versioned docs, so every docs
// version shows the current list of layers.
const LAMBDA_LAYER_CATALOG_URL =
  "https://docs.developer.albertinvent.com/albert-python/lambda-layers.json";

const LAMBDA_LAYER_FILTERS = [
  { key: "sdk_version", label: "SDK version" },
  { key: "python", label: "Python" },
  { key: "architecture", label: "Architecture" },
  { key: "region", label: "Region" },
];

function renderLambdaLayerCatalog(container, catalog) {
  const layers = catalog.layers || [];
  container.replaceChildren();

  const filters = document.createElement("div");
  filters.className = "lambda-layer-filters";
  const selects = {};
  for (const { key, label } of LAMBDA_LAYER_FILTERS) {
    // The catalog is sorted newest SDK version first; keep that order for the options.
    const values = [...new Set(layers.map((layer) => layer[key]).filter(Boolean))];
    if (key !== "sdk_version") {
      values.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
    }
    const select = document.createElement("select");
    select.add(new Option("All", ""));
    for (const value of values) select.add(new Option(value, value));
    if (key === "sdk_version" && values.length) select.value = values[0];
    const wrapper = document.createElement("label");
    wrapper.append(`${label} `, select);
    filters.append(wrapper);
    selects[key] = select;
  }

  const table = document.createElement("table");
  table.innerHTML =
    "<thead><tr><th>SDK version</th><th>Python</th><th>Architecture</th>" +
    "<th>Region</th><th>Layer ARN</th></tr></thead>";
  const body = table.createTBody();
  const scrollWrap = document.createElement("div");
  scrollWrap.className = "md-typeset__scrollwrap";
  const tableWrap = document.createElement("div");
  tableWrap.className = "md-typeset__table";
  tableWrap.append(table);
  scrollWrap.append(tableWrap);

  const summary = document.createElement("p");

  function update() {
    const rows = layers.filter((layer) =>
      LAMBDA_LAYER_FILTERS.every(
        ({ key }) => !selects[key].value || layer[key] === selects[key].value,
      ),
    );
    body.replaceChildren();
    for (const layer of rows) {
      const row = body.insertRow();
      for (const key of ["sdk_version", "python", "architecture", "region"]) {
        row.insertCell().textContent = layer[key] || "";
      }
      const arn = document.createElement("code");
      arn.textContent = layer.arn;
      row.insertCell().append(arn);
    }
    summary.textContent =
      `Showing ${rows.length} of ${layers.length} public layer versions. ` +
      `Updated ${catalog.generated_at}.`;
  }

  for (const select of Object.values(selects)) select.addEventListener("change", update);
  container.append(filters, scrollWrap, summary);
  update();
}

function loadLambdaLayerCatalog() {
  const container = document.getElementById("lambda-layer-catalog");
  if (!container) return;
  fetch(LAMBDA_LAYER_CATALOG_URL, { cache: "no-cache", signal: AbortSignal.timeout(10000) })
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then((catalog) => renderLambdaLayerCatalog(container, catalog))
    .catch(() => {
      container.innerHTML =
        "<p>The layer list could not be loaded. Download " +
        `<a href="${LAMBDA_LAYER_CATALOG_URL}">lambda-layers.json</a> directly, or see the ` +
        '<a href="https://github.com/albert-labs/albert-python/releases">GitHub releases</a>.</p>';
    });
}

// Material's instant navigation swaps pages without a full reload; document$ fires on each.
if (typeof document$ !== "undefined") {
  document$.subscribe(loadLambdaLayerCatalog);
} else {
  document.addEventListener("DOMContentLoaded", loadLambdaLayerCatalog);
}
