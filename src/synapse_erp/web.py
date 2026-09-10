"""HTML/CSS/JS shell for the Synapse ERP startup platform."""

PLATFORM_HTML = r"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Synapse ERP Platform</title>
    <style>
        :root {
            --ink: #14201f;
            --muted: #5f6f76;
            --paper: #f5f4ee;
            --panel: #ffffff;
            --line: #d9ded7;
            --green: #1f7a5b;
            --blue: #255f99;
            --amber: #b77918;
            --red: #a74646;
            --soft-green: #e8f4ef;
            --soft-blue: #eaf0f8;
            --soft-amber: #fff5df;
        }
        * {
            box-sizing: border-box;
        }
        body {
            margin: 0;
            font-family: Aptos, Inter, Arial, sans-serif;
            color: var(--ink);
            background: var(--paper);
        }
        button, input, textarea {
            font: inherit;
        }
        button {
            cursor: pointer;
        }
        .topbar {
            position: sticky;
            top: 0;
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            min-height: 68px;
            padding: 14px 28px;
            background: rgba(255, 255, 255, 0.94);
            border-bottom: 1px solid var(--line);
            backdrop-filter: blur(10px);
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 220px;
        }
        .brand-mark {
            display: grid;
            place-items: center;
            width: 38px;
            height: 38px;
            border-radius: 8px;
            background: var(--green);
            color: white;
            font-weight: 800;
        }
        .brand strong {
            display: block;
            font-size: 18px;
            letter-spacing: 0;
        }
        .brand span {
            color: var(--muted);
            font-size: 12px;
        }
        .status-strip {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 8px;
        }
        .status-chip {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            min-height: 30px;
            padding: 5px 9px;
            border: 1px solid var(--line);
            border-radius: 999px;
            background: #f8faf8;
            color: var(--muted);
            font-size: 12px;
        }
        .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--green);
        }
        .shell {
            display: grid;
            grid-template-columns: 410px minmax(0, 1fr);
            min-height: calc(100vh - 68px);
        }
        .left-pane {
            padding: 24px;
            border-right: 1px solid var(--line);
            background: #fbfbf7;
        }
        .main-pane {
            min-width: 0;
            padding: 24px;
        }
        .hero {
            display: grid;
            grid-template-columns: minmax(0, 1fr) 360px;
            gap: 18px;
            margin-bottom: 18px;
            align-items: stretch;
        }
        .hero-copy, .visual-panel, .input-panel, .pipeline-panel, .result-panel, .table-panel {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
        }
        .hero-copy {
            padding: 24px;
        }
        .kicker {
            margin: 0 0 8px;
            color: var(--green);
            font-size: 13px;
            font-weight: 700;
        }
        h1 {
            margin: 0;
            font-size: 42px;
            line-height: 1.04;
            letter-spacing: 0;
            max-width: 760px;
        }
        .hero-copy p {
            margin: 14px 0 0;
            color: var(--muted);
            font-size: 17px;
            line-height: 1.55;
            max-width: 760px;
        }
        .visual-panel {
            overflow: hidden;
            min-height: 220px;
            background: var(--soft-blue);
        }
        .visual-panel img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        .input-panel {
            padding: 18px;
        }
        .input-panel h2, .pipeline-panel h2, .result-panel h2, .table-panel h2 {
            margin: 0 0 14px;
            font-size: 20px;
            letter-spacing: 0;
        }
        .field {
            margin-bottom: 16px;
        }
        label {
            display: block;
            margin-bottom: 7px;
            font-size: 13px;
            color: var(--muted);
            font-weight: 700;
        }
        input[type="file"], textarea {
            width: 100%;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: white;
        }
        input[type="file"] {
            padding: 11px;
            min-height: 46px;
        }
        textarea {
            min-height: 118px;
            resize: vertical;
            padding: 12px;
            color: var(--ink);
            line-height: 1.45;
        }
        .output-contract {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin: 12px 0 18px;
        }
        .format-pill {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #f8faf8;
            padding: 9px 10px;
            color: var(--ink);
            font-size: 13px;
        }
        .actions {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .primary, .secondary {
            min-height: 44px;
            border-radius: 8px;
            border: 1px solid transparent;
            font-weight: 800;
        }
        .primary {
            background: var(--green);
            color: white;
        }
        .secondary {
            background: white;
            color: var(--blue);
            border-color: var(--line);
        }
        .primary:disabled, .secondary:disabled {
            opacity: 0.55;
            cursor: wait;
        }
        .preview-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin-top: 14px;
        }
        .preview {
            overflow: hidden;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #f9faf9;
            min-height: 92px;
        }
        .preview img {
            width: 100%;
            height: 120px;
            object-fit: cover;
            display: block;
        }
        .preview span {
            display: block;
            padding: 8px;
            color: var(--muted);
            font-size: 12px;
            overflow-wrap: anywhere;
        }
        .pipeline-panel {
            padding: 18px;
            margin-bottom: 18px;
        }
        .nodes {
            display: grid;
            grid-template-columns: repeat(9, minmax(116px, 1fr));
            gap: 10px;
            overflow-x: auto;
            padding-bottom: 4px;
        }
        .node {
            min-height: 136px;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 12px;
            background: #fbfcfb;
        }
        .node.done {
            border-color: #b5d8c9;
            background: var(--soft-green);
        }
        .node.running {
            border-color: #c7d6ec;
            background: var(--soft-blue);
        }
        .node strong {
            display: block;
            margin: 8px 0 6px;
            font-size: 14px;
            letter-spacing: 0;
        }
        .node p {
            margin: 0;
            color: var(--muted);
            font-size: 12px;
            line-height: 1.38;
        }
        .node .status {
            display: inline-flex;
            align-items: center;
            min-height: 24px;
            padding: 3px 7px;
            border-radius: 999px;
            background: white;
            color: var(--green);
            font-size: 11px;
            font-weight: 800;
            border: 1px solid #cfe4db;
        }
        .result-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
            margin-bottom: 18px;
        }
        .result-panel {
            padding: 18px;
        }
        .metric {
            min-height: 118px;
        }
        .metric span {
            color: var(--muted);
            font-size: 13px;
            font-weight: 700;
        }
        .metric strong {
            display: block;
            margin-top: 10px;
            font-size: 28px;
            letter-spacing: 0;
        }
        .workspace-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.2fr) minmax(360px, 0.8fr);
            gap: 18px;
        }
        .table-panel {
            padding: 18px;
            overflow: hidden;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        th, td {
            padding: 10px 8px;
            border-bottom: 1px solid var(--line);
            text-align: left;
            vertical-align: top;
        }
        th {
            color: var(--muted);
            font-size: 12px;
        }
        .downloads {
            display: grid;
            gap: 9px;
        }
        .download-link {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 10px 12px;
            text-decoration: none;
            color: var(--ink);
            background: #fbfcfb;
        }
        .download-link span {
            color: var(--muted);
            font-size: 12px;
            text-transform: uppercase;
        }
        .empty-state {
            display: grid;
            place-items: center;
            min-height: 220px;
            border: 1px dashed #bdc8c2;
            border-radius: 8px;
            color: var(--muted);
            text-align: center;
            padding: 18px;
        }
        .notice {
            margin: 12px 0 0;
            padding: 11px 12px;
            border-left: 4px solid var(--amber);
            border-radius: 6px;
            color: #61440d;
            background: var(--soft-amber);
            font-size: 13px;
            line-height: 1.4;
        }
        @media (max-width: 1180px) {
            .shell, .hero, .workspace-grid {
                grid-template-columns: 1fr;
            }
            .left-pane {
                border-right: 0;
                border-bottom: 1px solid var(--line);
            }
            .result-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        @media (max-width: 720px) {
            .topbar {
                align-items: flex-start;
                flex-direction: column;
                padding: 14px 16px;
            }
            .left-pane, .main-pane {
                padding: 16px;
            }
            h1 {
                font-size: 32px;
            }
            .actions, .output-contract, .result-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <header class="topbar">
        <div class="brand">
            <div class="brand-mark">S</div>
            <div>
                <strong>Synapse ERP</strong>
                <span>Offline-to-SaaS conversion platform</span>
            </div>
        </div>
        <div id="serviceStatus" class="status-strip"></div>
    </header>

    <div class="shell">
        <aside class="left-pane">
            <form id="convertForm" class="input-panel">
                <h2>Conversion Desk</h2>
                <div class="field">
                    <label for="ledgerImages">Handwritten note images</label>
                    <input id="ledgerImages" name="ledger_images" type="file" accept="image/*" multiple>
                </div>
                <div class="field">
                    <label for="productImages">Product photos</label>
                    <input id="productImages" name="product_images" type="file" accept="image/*" multiple>
                </div>
                <div class="field">
                    <label for="productHints">Product names or SKU hints</label>
                    <textarea id="productHints" name="product_hints" placeholder="One operator-confirmed label per photo"></textarea>
                </div>
                <div class="field">
                    <label for="ledgerText">OCR assist text</label>
                    <textarea id="ledgerText" name="ledger_text" placeholder="2026-09-10 ramesh: chini 2 kg Rs 88"></textarea>
                </div>
                <div class="field">
                    <label for="chatText">WhatsApp chat orders</label>
                    <textarea id="chatText" name="chat_text" placeholder="kavya: 2 kg atta Rs 76"></textarea>
                </div>
                <label>Output contract</label>
                <div class="output-contract">
                    <div class="format-pill">JSON API</div>
                    <div class="format-pill">CSV exports</div>
                    <div class="format-pill">ERP HTML</div>
                    <div class="format-pill">Report MD</div>
                </div>
                <div class="actions">
                    <button class="primary" id="runButton" type="submit">Run conversion</button>
                </div>
                <div class="notice">No sample rows are injected. Ledger images use the installed CRNN checkpoint, and unreadable results request an explicit transcription.</div>
                <div id="localPreviews" class="preview-grid"></div>
            </form>
        </aside>

        <main class="main-pane">
            <section class="hero">
                <div class="hero-copy">
                    <p class="kicker">Multimodal DL + OCR engine</p>
                    <h1>Upload khata photos, product images, and chat orders. Get a live ERP back.</h1>
                    <p>Every conversion runs through visible backend nodes: OCR, product vision, order NER, business graph, forecasting, ERP builder, and exporters.</p>
                </div>
                <div class="visual-panel">
                    <img src="/project-assets/architecture.png" alt="Synapse ERP backend architecture">
                </div>
            </section>

            <section class="pipeline-panel">
                <h2>Backend Nodes</h2>
                <div id="nodes" class="nodes"></div>
            </section>

            <section id="emptyState" class="empty-state">
                <div>
                    <strong>Conversion output appears here.</strong>
                    <p>Run a conversion to see structured inventory, CRM, invoices, product catalog, and export files.</p>
                </div>
            </section>

            <section id="results" hidden>
                <div class="result-grid">
                    <div class="result-panel metric"><span>Total revenue</span><strong id="metricRevenue">Rs 0</strong></div>
                    <div class="result-panel metric"><span>Total orders</span><strong id="metricOrders">0</strong></div>
                    <div class="result-panel metric"><span>Top SKU</span><strong id="metricTopSku">None</strong></div>
                    <div class="result-panel metric"><span>Conversion ID</span><strong id="metricConversion">-</strong></div>
                </div>

                <div class="workspace-grid">
                    <div class="table-panel">
                        <h2>Inventory Output</h2>
                        <div id="inventoryTable"></div>
                    </div>
                    <div class="table-panel">
                        <h2>Exports</h2>
                        <div id="downloads" class="downloads"></div>
                    </div>
                    <div class="table-panel">
                        <h2>Product Photo Enrollment</h2>
                        <div id="productTable"></div>
                    </div>
                    <div class="table-panel">
                        <h2>Uploaded Image Assets</h2>
                        <div id="assetGrid" class="preview-grid"></div>
                    </div>
                </div>
            </section>
        </main>
    </div>

    <script>
        const serviceStatus = document.getElementById("serviceStatus");
        const nodesEl = document.getElementById("nodes");
        const form = document.getElementById("convertForm");
        const runButton = document.getElementById("runButton");
        const emptyState = document.getElementById("emptyState");
        const results = document.getElementById("results");
        const localPreviews = document.getElementById("localPreviews");

        function escapeHtml(value) {
            return String(value ?? "").replace(/[&<>"']/g, (char) => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#039;"
            }[char]));
        }

        function money(value) {
            return `Rs ${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
        }

        function renderServices(services) {
            serviceStatus.innerHTML = services.slice(0, 6).map((service) => `
                <span class="status-chip"><span class="dot"></span>${escapeHtml(service.name)}</span>
            `).join("");
            renderNodes(services.map((service) => ({ ...service, status: service.status || "online", detail: service.role })));
        }

        function renderNodes(nodes) {
            nodesEl.innerHTML = nodes.map((node) => {
                const done = ["completed", "online"].includes(node.status) ? "done" : "running";
                return `
                    <article class="node ${done}">
                        <span class="status">${escapeHtml(node.status)}</span>
                        <strong>${escapeHtml(node.name)}</strong>
                        <p>${escapeHtml(node.detail || node.role)}</p>
                        ${node.latency_ms ? `<p>${node.latency_ms} ms</p>` : ""}
                    </article>
                `;
            }).join("");
        }

        function tableFromRows(rows, columns) {
            if (!rows || !rows.length) {
                return `<div class="empty-state">No rows yet.</div>`;
            }
            return `
                <table>
                    <thead><tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr></thead>
                    <tbody>
                        ${rows.map((row) => `
                            <tr>${columns.map((column) => `<td>${escapeHtml(column.format ? column.format(row[column.key], row) : row[column.key])}</td>`).join("")}</tr>
                        `).join("")}
                    </tbody>
                </table>
            `;
        }

        function renderResult(result) {
            const analytics = result.snapshot.analytics || {};
            document.getElementById("metricRevenue").textContent = money(analytics.total_revenue);
            document.getElementById("metricOrders").textContent = analytics.total_orders || 0;
            document.getElementById("metricTopSku").textContent = analytics.top_sku || "None";
            document.getElementById("metricConversion").textContent = result.conversion_id.replace("conv-", "");

            renderNodes(result.nodes);
            document.getElementById("inventoryTable").innerHTML = tableFromRows(result.snapshot.inventory, [
                { key: "display_name", label: "SKU" },
                { key: "quantity_sold", label: "Sold" },
                { key: "unit", label: "Unit" },
                { key: "revenue", label: "Revenue", format: money },
                { key: "reorder_hint", label: "Restock" }
            ]);
            document.getElementById("productTable").innerHTML = tableFromRows(result.product_catalog, [
                { key: "display_name", label: "Product" },
                { key: "sku", label: "SKU" },
                { key: "source", label: "Label source" },
                { key: "status", label: "Status" }
            ]);
            document.getElementById("downloads").innerHTML = result.outputs.map((output) => `
                <a class="download-link" href="${escapeHtml(output.url)}" target="_blank" rel="noreferrer">
                    <strong>${escapeHtml(output.label)}</strong>
                    <span>${escapeHtml(output.format)}</span>
                </a>
            `).join("");
            document.getElementById("assetGrid").innerHTML = result.assets.length ? result.assets.map((asset) => `
                <div class="preview">
                    <img src="${escapeHtml(asset.url)}" alt="${escapeHtml(asset.filename)}">
                    <span>${escapeHtml(asset.kind)} | ${escapeHtml(asset.filename)} | ${escapeHtml(asset.signal)}</span>
                </div>
            `).join("") : `<div class="empty-state">No images uploaded for this run.</div>`;
            emptyState.hidden = true;
            results.hidden = false;
        }

        function setBusy(isBusy) {
            runButton.disabled = isBusy;
            runButton.textContent = isBusy ? "Converting..." : "Run conversion";
        }

        async function loadServices() {
            const response = await fetch("/api/services");
            renderServices((await response.json()).services);
        }

        async function runConversion(event) {
            event.preventDefault();
            setBusy(true);
            try {
                const payload = new FormData(form);
                const response = await fetch("/api/convert", { method: "POST", body: payload });
                if (!response.ok) {
                    throw new Error(await response.text());
                }
                renderResult(await response.json());
            } finally {
                setBusy(false);
            }
        }

        function renderLocalPreviews() {
            const files = [
                ...document.getElementById("ledgerImages").files,
                ...document.getElementById("productImages").files
            ];
            localPreviews.innerHTML = files.slice(0, 6).map((file) => `
                <div class="preview">
                    <img src="${URL.createObjectURL(file)}" alt="${escapeHtml(file.name)}">
                    <span>${escapeHtml(file.name)}</span>
                </div>
            `).join("");
        }

        form.addEventListener("submit", runConversion);
        document.getElementById("ledgerImages").addEventListener("change", renderLocalPreviews);
        document.getElementById("productImages").addEventListener("change", renderLocalPreviews);
        loadServices();
    </script>
</body>
</html>
"""
