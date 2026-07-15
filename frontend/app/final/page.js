"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Download, FileJson, LineChart, ShieldCheck } from "lucide-react";
import { absoluteUrl, formatMoney, loadConversion, loadWorkspace } from "../lib/flow";

export default function FinalPage() {
  const [conversion, setConversion] = useState(null);
  const [workspace, setWorkspace] = useState(null);

  useEffect(() => {
    setConversion(loadConversion());
    setWorkspace(loadWorkspace());
  }, []);

  const analytics = workspace?.analytics || conversion?.snapshot?.analytics || {};
  const outputs = conversion?.outputs || [];

  return (
    <main className="flow-page">
      <section className="step-shell">
        <div className="step-intro">
          <p className="eyebrow">Final step</p>
          <h1>Your offline-to-SaaS conversion package is ready.</h1>
          <p>Use this page for final demo handoff: generated ERP, protected workspace, exports, and next development milestones.</p>
        </div>

        <div className="final-grid">
          <article className="metric-card">
            <span>Total revenue</span>
            <strong>{formatMoney(analytics.total_revenue)}</strong>
          </article>
          <article className="metric-card">
            <span>Total orders</span>
            <strong>{analytics.total_orders || 0}</strong>
          </article>
          <article className="metric-card">
            <span>Top SKU</span>
            <strong>{analytics.top_sku || "Not converted"}</strong>
          </article>
          <article className="metric-card">
            <span>Workspace</span>
            <strong>{workspace ? "Authenticated" : "Not opened"}</strong>
          </article>
        </div>

        <div className="final-content-grid">
          <section className="step-card">
            <h2>Downloadable outputs</h2>
            <div className="download-grid final-downloads">
              {outputs.length ? outputs.map((output) => (
                <a href={absoluteUrl(output.url)} target="_blank" rel="noreferrer" key={output.url}>
                  <Download size={16} />
                  <span>{output.label}</span>
                  <small>{output.format}</small>
                </a>
              )) : (
                <div className="empty-download">No outputs yet. Start from Step 1.</div>
              )}
            </div>
          </section>

          <section className="step-card">
            <h2>What is now possible</h2>
            <div className="capability-list">
              <p><FileJson size={17} /> Structured JSON and CSV data for integration.</p>
              <p><ShieldCheck size={17} /> Authenticated generated ERP workspace with CRUD.</p>
              <p><LineChart size={17} /> Forecast-ready analytics layer for inventory decisions.</p>
            </div>
          </section>
        </div>

        <section className="step-card roadmap-card">
          <h2>Future development path</h2>
          <div className="roadmap-grid">
            <div><strong>Phase 1</strong><span>Train OCR + forecasting models, add metrics, final report.</span></div>
            <div><strong>Phase 2</strong><span>PostgreSQL, real JWT/OAuth, role-based access, audit logs.</span></div>
            <div><strong>Phase 3</strong><span>Fine-tune TrOCR, MuRIL NER, product metric learning.</span></div>
            <div><strong>Phase 4</strong><span>Field pilot with shop data, WhatsApp Business API, offline mobile capture.</span></div>
          </div>
        </section>

        <div className="step-actions">
          <Link href="/step-4" className="secondary-button">Back to workspace</Link>
          <Link href="/step-1" className="primary-button">Start another conversion</Link>
        </div>
      </section>
    </main>
  );
}
