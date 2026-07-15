"""Standalone ERP HTML renderer with built-in auth and CRUD."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from synapse_erp.config import OUTPUT_DIR
from synapse_erp.schema import BusinessSnapshot


def render_erp_html(snapshot: BusinessSnapshot, output_dir: Path | None = None) -> Path:
    output_dir = output_dir or (OUTPUT_DIR / "erp")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "index.html"
    path.write_text(_html(snapshot), encoding="utf-8")
    return path


def _html(snapshot: BusinessSnapshot) -> str:
    initial_data = json.dumps(snapshot.to_dict(), ensure_ascii=False).replace("</", "<\\/")
    generated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Synapse ERP</title>
  <style>
    :root {
      --ink: #17211f;
      --muted: #66736f;
      --paper: #f3f1e9;
      --panel: #ffffff;
      --line: #d9ddd5;
      --green: #1f7a5b;
      --mint: #dff5ec;
      --blue: #255f99;
      --amber: #bd7b16;
      --red: #ad4640;
      --dark: #0d1110;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      background: var(--paper);
      font-family: Aptos, Inter, Arial, sans-serif;
    }
    button, input, select { font: inherit; }
    button { cursor: pointer; }
    .login-screen {
      display: grid;
      grid-template-columns: minmax(320px, 0.85fr) minmax(0, 1.15fr);
      min-height: 100vh;
    }
    .login-copy {
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding: clamp(28px, 6vw, 78px);
      color: #f7f4ec;
      background:
        radial-gradient(circle at 18% 20%, rgba(127, 227, 180, 0.18), transparent 28%),
        linear-gradient(150deg, #0a0f0d, #121714 60%, #080a09);
    }
    .login-copy h1 {
      margin: 0;
      max-width: 720px;
      font-size: clamp(44px, 7vw, 90px);
      line-height: 0.95;
      letter-spacing: 0;
    }
    .login-copy p {
      max-width: 620px;
      color: #b6c1bd;
      font-size: 18px;
      line-height: 1.58;
    }
    .login-panel-wrap {
      display: grid;
      place-items: center;
      padding: 28px;
    }
    .login-panel {
      width: min(420px, 100%);
      padding: 24px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel);
      box-shadow: 0 24px 70px rgba(23, 33, 31, 0.14);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 24px;
    }
    .brand-mark {
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border-radius: 10px;
      background: linear-gradient(135deg, #7fe3b4, #f4bd61);
      color: #07100d;
      font-weight: 900;
    }
    .brand strong, .brand span { display: block; }
    .brand span { color: var(--muted); font-size: 13px; }
    label {
      display: block;
      margin: 13px 0 7px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }
    input, select {
      width: 100%;
      min-height: 42px;
      padding: 10px 11px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfa;
      color: var(--ink);
    }
    .primary, .secondary, .danger {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 40px;
      padding: 9px 12px;
      border-radius: 8px;
      border: 1px solid transparent;
      font-weight: 800;
    }
    .primary {
      color: white;
      background: var(--green);
    }
    .secondary {
      color: var(--ink);
      background: white;
      border-color: var(--line);
    }
    .danger {
      color: white;
      background: var(--red);
    }
    .login-panel .primary { width: 100%; margin-top: 18px; }
    .helper {
      margin: 12px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }
    .error {
      margin: 12px 0 0;
      color: var(--red);
      font-size: 13px;
      font-weight: 700;
    }
    .app { display: none; min-height: 100vh; }
    .sidebar {
      position: fixed;
      inset: 0 auto 0 0;
      width: 250px;
      padding: 18px;
      background: var(--dark);
      color: #eef4ef;
    }
    .sidebar .brand { margin-bottom: 26px; }
    .nav-button {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      min-height: 42px;
      margin-bottom: 8px;
      padding: 10px 11px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px;
      color: #b9c3bf;
      background: rgba(255, 255, 255, 0.04);
      text-align: left;
    }
    .nav-button.active {
      color: #07100d;
      background: #7fe3b4;
    }
    .sidebar-footer {
      position: absolute;
      left: 18px;
      right: 18px;
      bottom: 18px;
      color: #95a39e;
      font-size: 12px;
      line-height: 1.45;
    }
    .main {
      min-height: 100vh;
      margin-left: 250px;
      padding: 22px;
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 18px;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
    }
    .topbar h1 { margin: 0; font-size: 28px; letter-spacing: 0; }
    .topbar p { margin: 5px 0 0; color: var(--muted); }
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 9px;
      align-items: center;
      justify-content: flex-end;
    }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .metric {
      min-height: 108px;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
    }
    .metric span {
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }
    .metric strong {
      display: block;
      margin-top: 10px;
      font-size: 27px;
      overflow-wrap: anywhere;
    }
    .panel {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
      overflow: hidden;
    }
    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 16px;
      border-bottom: 1px solid var(--line);
    }
    .panel-head h2 { margin: 0; font-size: 20px; letter-spacing: 0; }
    .panel-head p { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
    .search {
      max-width: 280px;
      min-height: 38px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }
    th, td {
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      background: #f8faf7;
    }
    .row-actions {
      display: flex;
      gap: 7px;
    }
    .row-actions button {
      min-height: 30px;
      padding: 5px 8px;
      border-radius: 6px;
      border: 1px solid var(--line);
      background: white;
    }
    .row-actions .delete { color: var(--red); }
    .analytics-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 14px;
      padding: 16px;
    }
    .bar-row {
      display: grid;
      grid-template-columns: 130px 1fr 110px;
      gap: 12px;
      align-items: center;
      margin-bottom: 14px;
      font-size: 14px;
    }
    .bar-track {
      height: 12px;
      border-radius: 999px;
      overflow: hidden;
      background: #e7ece8;
    }
    .bar-fill {
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--green), var(--blue));
    }
    .callout {
      padding: 13px;
      border-left: 4px solid var(--amber);
      border-radius: 8px;
      background: #fff7e8;
      color: #5f430d;
      line-height: 1.45;
    }
    .modal-backdrop {
      position: fixed;
      inset: 0;
      display: none;
      place-items: center;
      padding: 18px;
      background: rgba(7, 10, 9, 0.62);
      z-index: 10;
    }
    .modal {
      width: min(720px, 100%);
      max-height: 92vh;
      overflow: auto;
      padding: 18px;
      border-radius: 12px;
      background: white;
      box-shadow: 0 28px 90px rgba(0, 0, 0, 0.34);
    }
    .modal h2 { margin: 0 0 4px; }
    .modal p { margin: 0 0 14px; color: var(--muted); }
    .form-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 9px;
      margin-top: 16px;
    }
    .hidden { display: none !important; }
    @media (max-width: 1020px) {
      .sidebar { position: static; width: auto; }
      .sidebar-footer { position: static; margin-top: 18px; }
      .main { margin-left: 0; }
      .metric-grid, .analytics-grid { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 680px) {
      .login-screen, .metric-grid, .analytics-grid, .form-grid { grid-template-columns: 1fr; }
      .topbar, .panel-head { display: block; }
      .toolbar { justify-content: flex-start; margin-top: 12px; }
      .main { padding: 12px; }
      .bar-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <section id="loginScreen" class="login-screen">
    <div class="login-copy">
      <p class="helper">Synapse ERP</p>
      <h1>A complete shop system from offline records.</h1>
      <p>This generated ERP includes authentication, inventory CRUD, customer CRM, invoice management, analytics, and local export tools inside this single HTML file.</p>
    </div>
    <div class="login-panel-wrap">
      <form id="loginForm" class="login-panel">
        <div class="brand">
          <div class="brand-mark">S</div>
          <div>
            <strong>Synapse ERP</strong>
            <span>Secure shop workspace</span>
          </div>
        </div>
        <label for="shopId">Shop ID</label>
        <input id="shopId" value="synapse-demo" autocomplete="username">
        <label for="pin">Owner PIN</label>
        <input id="pin" type="password" value="1234" autocomplete="current-password">
        <button class="primary" type="submit">Login to ERP</button>
        <p class="helper">Demo credentials: <strong>synapse-demo</strong> / <strong>1234</strong>. Changes are saved locally in this browser.</p>
        <p id="loginError" class="error"></p>
      </form>
    </div>
  </section>

  <section id="app" class="app">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">S</div>
        <div>
          <strong>Synapse ERP</strong>
          <span>Generated workspace</span>
        </div>
      </div>
      <button class="nav-button active" data-view="inventory">Inventory <span id="navInventoryCount">0</span></button>
      <button class="nav-button" data-view="customers">Customers <span id="navCustomerCount">0</span></button>
      <button class="nav-button" data-view="invoices">Invoices <span id="navInvoiceCount">0</span></button>
      <button class="nav-button" data-view="analytics">Analytics <span>Live</span></button>
      <div class="sidebar-footer">
        Generated at __GENERATED_AT__<br>
        Local CRUD store: browser localStorage
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <h1 id="pageTitle">Inventory Manager</h1>
          <p id="pageSubtitle">Add, edit, delete, search, and export generated inventory rows.</p>
        </div>
        <div class="toolbar">
          <button id="addButton" class="primary">Add row</button>
          <button id="resetButton" class="secondary">Reset generated data</button>
          <button id="logoutButton" class="secondary">Logout</button>
        </div>
      </header>

      <section class="metric-grid">
        <div class="metric"><span>Total revenue</span><strong id="metricRevenue">Rs 0</strong></div>
        <div class="metric"><span>Total orders</span><strong id="metricOrders">0</strong></div>
        <div class="metric"><span>Top SKU</span><strong id="metricTopSku">None</strong></div>
        <div class="metric"><span>Invoices</span><strong id="metricInvoices">0</strong></div>
      </section>

      <section id="crudPanel" class="panel">
        <div class="panel-head">
          <div>
            <h2 id="tableTitle">Inventory</h2>
            <p id="tableSubtitle">Generated rows are editable like a normal ERP table.</p>
          </div>
          <div class="toolbar">
            <input id="searchBox" class="search" placeholder="Search rows">
            <button id="exportCsvButton" class="secondary">Export CSV</button>
            <button id="exportJsonButton" class="secondary">Export JSON</button>
          </div>
        </div>
        <div id="tableWrap"></div>
      </section>

      <section id="analyticsPanel" class="panel hidden">
        <div class="panel-head">
          <div>
            <h2>Analytics</h2>
            <p>Live analytics update after CRUD changes.</p>
          </div>
        </div>
        <div class="analytics-grid">
          <div id="barChart"></div>
          <div>
            <div id="forecastCallout" class="callout"></div>
            <br>
            <div id="anomalyCallout" class="callout"></div>
          </div>
        </div>
      </section>
    </main>
  </section>

  <div id="modalBackdrop" class="modal-backdrop">
    <form id="editForm" class="modal">
      <h2 id="modalTitle">Edit row</h2>
      <p id="modalSubtitle">Update fields and save changes.</p>
      <div id="formGrid" class="form-grid"></div>
      <div class="modal-actions">
        <button type="button" id="cancelButton" class="secondary">Cancel</button>
        <button type="submit" class="primary">Save row</button>
      </div>
    </form>
  </div>

  <script>
    const INITIAL_DATA = __INITIAL_DATA__;
    const STORAGE_KEY = "synapse-generated-erp:" + location.pathname + ":" + (INITIAL_DATA.analytics?.total_orders || 0);
    const SESSION_KEY = STORAGE_KEY + ":session";
    const schemas = {
      inventory: [
        ["sku", "SKU", "text"],
        ["display_name", "Display name", "text"],
        ["unit", "Unit", "text"],
        ["quantity_sold", "Quantity sold", "number"],
        ["revenue", "Revenue", "number"],
        ["reorder_hint", "Restock hint", "number"]
      ],
      customers: [
        ["name", "Name", "text"],
        ["orders", "Orders", "number"],
        ["revenue", "Revenue", "number"],
        ["last_item", "Last item", "text"],
        ["credit_risk", "Credit risk", "text"]
      ],
      invoices: [
        ["invoice_id", "Invoice ID", "text"],
        ["customer", "Customer", "text"],
        ["item", "Item", "text"],
        ["quantity", "Quantity", "number"],
        ["unit", "Unit", "text"],
        ["amount", "Amount", "number"]
      ]
    };
    const keys = { inventory: "sku", customers: "name", invoices: "invoice_id" };
    const titles = {
      inventory: ["Inventory Manager", "Add, edit, delete, search, and export generated inventory rows.", "Inventory"],
      customers: ["Customer CRM", "Manage customer profiles generated from ledger and chat orders.", "Customers"],
      invoices: ["Invoice Manager", "Create and update invoices from converted chat orders.", "Invoices"]
    };
    let state = loadState();
    let activeView = "inventory";
    let editingId = null;

    const loginScreen = document.getElementById("loginScreen");
    const app = document.getElementById("app");
    const tableWrap = document.getElementById("tableWrap");
    const searchBox = document.getElementById("searchBox");
    const modalBackdrop = document.getElementById("modalBackdrop");
    const formGrid = document.getElementById("formGrid");

    document.getElementById("loginForm").addEventListener("submit", (event) => {
      event.preventDefault();
      const shopId = document.getElementById("shopId").value.trim();
      const pin = document.getElementById("pin").value.trim();
      if (shopId === "synapse-demo" && pin === "1234") {
        localStorage.setItem(SESSION_KEY, "owner");
        showApp();
      } else {
        document.getElementById("loginError").textContent = "Invalid shop ID or PIN.";
      }
    });
    document.getElementById("logoutButton").addEventListener("click", () => {
      localStorage.removeItem(SESSION_KEY);
      loginScreen.style.display = "grid";
      app.style.display = "none";
    });
    document.getElementById("resetButton").addEventListener("click", () => {
      if (!confirm("Reset this ERP to the originally generated data?")) return;
      state = makeInitialState();
      saveState();
      render();
    });
    document.getElementById("addButton").addEventListener("click", () => openModal(null));
    document.getElementById("cancelButton").addEventListener("click", closeModal);
    document.getElementById("editForm").addEventListener("submit", saveModal);
    document.getElementById("exportCsvButton").addEventListener("click", () => downloadCsv(activeView));
    document.getElementById("exportJsonButton").addEventListener("click", () => downloadJson());
    searchBox.addEventListener("input", renderTable);
    document.querySelectorAll(".nav-button").forEach((button) => {
      button.addEventListener("click", () => {
        activeView = button.dataset.view;
        document.querySelectorAll(".nav-button").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        render();
      });
    });

    if (localStorage.getItem(SESSION_KEY)) {
      showApp();
    }

    function showApp() {
      loginScreen.style.display = "none";
      app.style.display = "block";
      render();
    }

    function makeInitialState() {
      return {
        inventory: INITIAL_DATA.inventory || [],
        customers: INITIAL_DATA.customers || [],
        invoices: INITIAL_DATA.invoices || [],
        analytics: INITIAL_DATA.analytics || {}
      };
    }

    function loadState() {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) return makeInitialState();
      try { return JSON.parse(saved); } catch { return makeInitialState(); }
    }

    function saveState() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }

    function render() {
      updateMetrics();
      updateCounts();
      document.getElementById("crudPanel").classList.toggle("hidden", activeView === "analytics");
      document.getElementById("analyticsPanel").classList.toggle("hidden", activeView !== "analytics");
      document.getElementById("addButton").classList.toggle("hidden", activeView === "analytics");
      searchBox.value = "";
      if (activeView === "analytics") {
        document.getElementById("pageTitle").textContent = "Analytics";
        document.getElementById("pageSubtitle").textContent = "Live analytics update after CRUD changes.";
        renderAnalytics();
      } else {
        const [title, subtitle, tableTitle] = titles[activeView];
        document.getElementById("pageTitle").textContent = title;
        document.getElementById("pageSubtitle").textContent = subtitle;
        document.getElementById("tableTitle").textContent = tableTitle;
        document.getElementById("tableSubtitle").textContent = "Generated rows are editable like a normal ERP table.";
        renderTable();
      }
    }

    function updateMetrics() {
      const totalRevenue = sum(state.inventory, "revenue");
      const totalOrders = sum(state.customers, "orders") || state.invoices.length;
      const top = [...state.inventory].sort((a, b) => Number(b.revenue || 0) - Number(a.revenue || 0))[0];
      document.getElementById("metricRevenue").textContent = money(totalRevenue);
      document.getElementById("metricOrders").textContent = totalOrders;
      document.getElementById("metricTopSku").textContent = top ? (top.display_name || top.sku) : "None";
      document.getElementById("metricInvoices").textContent = state.invoices.length;
    }

    function updateCounts() {
      document.getElementById("navInventoryCount").textContent = state.inventory.length;
      document.getElementById("navCustomerCount").textContent = state.customers.length;
      document.getElementById("navInvoiceCount").textContent = state.invoices.length;
    }

    function renderTable() {
      const rows = state[activeView] || [];
      const query = searchBox.value.trim().toLowerCase();
      const filtered = query ? rows.filter((row) => JSON.stringify(row).toLowerCase().includes(query)) : rows;
      const schema = schemas[activeView];
      if (!filtered.length) {
        tableWrap.innerHTML = '<div style="padding:18px;color:var(--muted)">No rows found.</div>';
        return;
      }
      tableWrap.innerHTML = `
        <table>
          <thead>
            <tr>${schema.map(([, label]) => `<th>${escapeHtml(label)}</th>`).join("")}<th>Actions</th></tr>
          </thead>
          <tbody>
            ${filtered.map((row) => `
              <tr>
                ${schema.map(([key]) => `<td>${escapeHtml(formatCell(key, row[key]))}</td>`).join("")}
                <td>
                  <div class="row-actions">
                    <button type="button" onclick="openModal('${escapeJs(String(row[keys[activeView]]))}')">Edit</button>
                    <button type="button" class="delete" onclick="deleteRow('${escapeJs(String(row[keys[activeView]]))}')">Delete</button>
                  </div>
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }

    function renderAnalytics() {
      const inventory = [...state.inventory].sort((a, b) => Number(b.revenue || 0) - Number(a.revenue || 0));
      const maxRevenue = Math.max(...inventory.map((item) => Number(item.revenue || 0)), 1);
      document.getElementById("barChart").innerHTML = inventory.slice(0, 8).map((item) => {
        const width = Math.round(Number(item.revenue || 0) / maxRevenue * 100);
        return `<div class="bar-row"><span>${escapeHtml(item.display_name || item.sku)}</span><div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div><strong>${money(item.revenue)}</strong></div>`;
      }).join("") || "<p>No inventory revenue yet.</p>";
      const top = inventory[0];
      document.getElementById("forecastCallout").textContent = top ? `Restock about ${top.reorder_hint || 1} ${top.unit || "unit"} of ${top.display_name || top.sku} next week.` : "No forecast yet.";
      const highInvoices = state.invoices.filter((invoice) => Number(invoice.amount || 0) > 1000).length;
      document.getElementById("anomalyCallout").textContent = highInvoices ? `${highInvoices} unusually high invoice rows need review.` : "No high-value invoice anomalies in the current workspace.";
    }

    window.openModal = function openModal(id) {
      editingId = id;
      const schema = schemas[activeView];
      const row = id ? state[activeView].find((item) => String(item[keys[activeView]]) === String(id)) : defaultRow(activeView);
      document.getElementById("modalTitle").textContent = id ? `Edit ${activeView} row` : `Add ${activeView} row`;
      document.getElementById("modalSubtitle").textContent = id ? `Editing ${id}` : "Create a new row in the generated ERP.";
      formGrid.innerHTML = schema.map(([key, label, type]) => `
        <label>
          ${escapeHtml(label)}
          <input name="${escapeHtml(key)}" type="${type}" value="${escapeHtml(row[key] ?? "")}" ${id && key === keys[activeView] ? "readonly" : ""}>
        </label>
      `).join("");
      modalBackdrop.style.display = "grid";
    }

    function closeModal() {
      editingId = null;
      modalBackdrop.style.display = "none";
    }

    function saveModal(event) {
      event.preventDefault();
      const schema = schemas[activeView];
      const form = new FormData(event.target);
      const row = {};
      schema.forEach(([key, , type]) => {
        const value = form.get(key);
        row[key] = type === "number" ? Number(value || 0) : String(value || "").trim();
      });
      const key = keys[activeView];
      if (!row[key]) {
        alert(`${key} is required.`);
        return;
      }
      const rows = state[activeView];
      if (editingId) {
        const index = rows.findIndex((item) => String(item[key]) === String(editingId));
        if (index >= 0) rows[index] = row;
      } else {
        if (rows.some((item) => String(item[key]) === String(row[key]))) {
          alert(`${row[key]} already exists.`);
          return;
        }
        rows.push(row);
      }
      saveState();
      closeModal();
      render();
    }

    window.deleteRow = function deleteRow(id) {
      if (!confirm(`Delete ${id}?`)) return;
      const key = keys[activeView];
      state[activeView] = state[activeView].filter((row) => String(row[key]) !== String(id));
      saveState();
      render();
    }

    function defaultRow(resource) {
      if (resource === "inventory") return { sku: `new_sku_${Date.now().toString().slice(-4)}`, display_name: "New SKU", unit: "kg", quantity_sold: 0, revenue: 0, reorder_hint: 1 };
      if (resource === "customers") return { name: `new_customer_${Date.now().toString().slice(-4)}`, orders: 0, revenue: 0, last_item: "None", credit_risk: "new" };
      return { invoice_id: `INV-${Date.now().toString().slice(-5)}`, customer: "walk-in", item: "new_item", quantity: 1, unit: "unit", amount: 0 };
    }

    function downloadJson() {
      downloadFile("synapse-erp-workspace.json", "application/json", JSON.stringify(state, null, 2));
    }

    function downloadCsv(resource) {
      const rows = state[resource] || [];
      const schema = schemas[resource];
      const header = schema.map(([key]) => key);
      const csvRows = [header.join(",")].concat(rows.map((row) => header.map((key) => csvEscape(row[key])).join(",")));
      downloadFile(`synapse-${resource}.csv`, "text/csv", csvRows.join("\\n"));
    }

    function downloadFile(filename, type, content) {
      const blob = new Blob([content], { type });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }

    function money(value) {
      return `Rs ${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
    }

    function sum(rows, key) {
      return rows.reduce((total, row) => total + Number(row[key] || 0), 0);
    }

    function formatCell(key, value) {
      return ["revenue", "amount"].includes(key) ? money(value) : value;
    }

    function csvEscape(value) {
      const text = String(value ?? "");
      return /[",\\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
    }

    function escapeJs(value) {
      return String(value ?? "").replace(/[\\\\']/g, "\\\\$&");
    }
  </script>
</body>
</html>
"""
    return html.replace("__INITIAL_DATA__", initial_data).replace("__GENERATED_AT__", generated_at)
