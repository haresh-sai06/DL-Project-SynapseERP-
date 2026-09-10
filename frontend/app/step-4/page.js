"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, KeyRound, Pencil, Plus, Save, Trash2 } from "lucide-react";
import { API_BASE, fetchWorkspace, getWorkspaceToken, loadConversion, loadWorkspace } from "../lib/flow";

const resourceKeys = {
  inventory: "sku",
  customers: "name",
  invoices: "invoice_id"
};

export default function WorkspacePage() {
  const [conversion, setConversion] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [activeResource, setActiveResource] = useState("inventory");
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const storedConversion = loadConversion();
    setConversion(storedConversion);
    setWorkspace(loadWorkspace());
    if (storedConversion?.conversion_id) {
      openWorkspace(storedConversion.conversion_id).catch(() => {});
    }
  }, []);

  const rows = workspace?.[activeResource] || [];
  const activeKey = resourceKeys[activeResource];

  async function runAction(action) {
    setError("");
    try {
      await action();
    } catch (actionError) {
      setError(actionError.message || "Workspace action failed.");
    }
  }

  async function openWorkspace(conversionId = conversion?.conversion_id) {
    if (!conversionId) {
      setMessage("Run a conversion first.");
      return;
    }
    const nextWorkspace = await fetchWorkspace(conversionId, conversion);
    setWorkspace(nextWorkspace);
    setMessage("Conversion-scoped access verified. Workspace is current.");
  }

  async function addRow() {
    if (!conversion?.conversion_id) return setMessage("Run a conversion first.");
    const token = getWorkspaceToken(conversion);
    const item = defaultItem(activeResource);
    const response = await fetch(`${API_BASE}/api/workspaces/${conversion.conversion_id}/${activeResource}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(item)
    });
    if (!response.ok) throw new Error(await response.text());
    await openWorkspace(conversion.conversion_id);
    setMessage(`Added ${item[activeKey]}.`);
  }

  function startEdit(row) {
    setEditing({ id: String(row[activeKey]), resource: activeResource });
    setDraft(JSON.stringify(row, null, 2));
  }

  async function saveEdit() {
    if (!editing || !conversion?.conversion_id) return;
    const token = getWorkspaceToken(conversion);
    const response = await fetch(
      `${API_BASE}/api/workspaces/${conversion.conversion_id}/${editing.resource}/${encodeURIComponent(editing.id)}`,
      {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: draft
      }
    );
    if (!response.ok) throw new Error(await response.text());
    setEditing(null);
    setDraft("");
    await openWorkspace(conversion.conversion_id);
    setMessage(`Saved ${editing.id}.`);
  }

  async function deleteRow(row) {
    if (!conversion?.conversion_id) return;
    const token = getWorkspaceToken(conversion);
    const itemId = String(row[activeKey]);
    const response = await fetch(
      `${API_BASE}/api/workspaces/${conversion.conversion_id}/${activeResource}/${encodeURIComponent(itemId)}`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    if (!response.ok) throw new Error(await response.text());
    await openWorkspace(conversion.conversion_id);
    setMessage(`Deleted ${itemId}.`);
  }

  if (!conversion) {
    return (
      <main className="flow-page">
        <section className="empty-step">
          <h1>No workspace yet</h1>
          <p>Run Step 1 first, then this page will open the generated ERP workspace with authentication and CRUD.</p>
          <Link href="/step-1" className="primary-button">Go to Step 1</Link>
        </section>
      </main>
    );
  }

  return (
    <main className="flow-page">
      <section className="step-shell">
        <div className="step-intro">
          <p className="eyebrow">Step 4</p>
          <h1>Work with the converted business records.</h1>
          <p>This workspace is protected by a token created for this conversion. Changes are persisted by the backend and reflected on refresh.</p>
        </div>

        <div className="step-card workspace-page-card">
          <div className="workspace-toolbar">
            <div className="resource-tabs">
              {["inventory", "customers", "invoices"].map((resource) => (
                <button
                  className={resource === activeResource ? "active" : ""}
                  key={resource}
                  onClick={() => {
                    setActiveResource(resource);
                    setEditing(null);
                    setDraft("");
                  }}
                  type="button"
                >
                  {resource}
                </button>
              ))}
            </div>
            <div className="button-row slim-buttons">
              <button className="secondary-button" type="button" onClick={() => runAction(() => openWorkspace())}>
                <KeyRound size={16} />
                Refresh data
              </button>
              <button className="primary-button" type="button" onClick={() => runAction(addRow)}>
                <Plus size={16} />
                Add row
              </button>
            </div>
          </div>

          {message && <p className="workspace-message">{message}</p>}
          {error && <p className="error">{error}</p>}

          <div className="crud-grid">
            <div className="table-card">
              <CrudTable rows={rows} resourceKey={activeKey} onEdit={startEdit} onDelete={(row) => runAction(() => deleteRow(row))} />
            </div>
            <div className="editor-card">
              <h3>Row editor</h3>
              <p>Select a row, review its complete record, and save a validated JSON update.</p>
              <textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Select a row to edit." />
              <button className="primary-button" type="button" disabled={!editing} onClick={() => runAction(saveEdit)}>
                <Save size={16} />
                Save changes
              </button>
            </div>
          </div>
        </div>

        <div className="step-actions">
          <Link href="/step-3" className="secondary-button">Back to preview</Link>
          <Link href="/final" className="primary-button">
            Final outputs
            <ArrowRight size={18} />
          </Link>
        </div>
      </section>
    </main>
  );
}

function CrudTable({ rows, resourceKey, onEdit, onDelete }) {
  if (!rows?.length) {
    return <div className="empty-table">Open the workspace to load rows.</div>;
  }
  const columns = Object.keys(rows[0]).slice(0, 5);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => <th key={column}>{column}</th>)}
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={String(row[resourceKey])}>
              {columns.map((column) => <td key={column}>{String(row[column] ?? "")}</td>)}
              <td>
                <div className="row-actions">
                  <button type="button" onClick={() => onEdit(row)}><Pencil size={14} /></button>
                  <button type="button" onClick={() => onDelete(row)}><Trash2 size={14} /></button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function defaultItem(resource) {
  if (resource === "inventory") {
    return {
      sku: `new_sku_${Date.now().toString().slice(-4)}`,
      display_name: "New SKU",
      unit: "kg",
      quantity_sold: 0,
      revenue: 0,
      reorder_hint: 1
    };
  }
  if (resource === "customers") {
    return {
      name: `new_customer_${Date.now().toString().slice(-4)}`,
      orders: 0,
      revenue: 0,
      last_item: "None",
      credit_risk: "new"
    };
  }
  return {
    invoice_id: `INV-${Date.now().toString().slice(-5)}`,
    customer: "walk-in",
    item: "new_item",
    quantity: 1,
    unit: "unit",
    amount: 0
  };
}
