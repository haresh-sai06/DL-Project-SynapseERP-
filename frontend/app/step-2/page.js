"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Boxes, BrainCircuit, Camera, ClipboardList, Download, Gauge, LineChart, Network, ReceiptText, Sparkles, Terminal, UploadCloud } from "lucide-react";
import { loadConversion } from "../lib/flow";

const nodeIcons = {
  gateway: UploadCloud,
  preprocess: Camera,
  ledger_ocr: ClipboardList,
  product_vision: Boxes,
  order_ner: BrainCircuit,
  graph: Network,
  forecast: LineChart,
  erp: ReceiptText,
  export: Download
};

export default function NodesPage() {
  const [conversion, setConversion] = useState(null);

  useEffect(() => {
    setConversion(loadConversion());
  }, []);

  if (!conversion) {
    return (
      <main className="flow-page">
        <EmptyStep title="No conversion yet" text="Start from Step 1 so the backend nodes have a conversion to display." />
      </main>
    );
  }

  return (
    <main className="flow-page">
      <section className="step-shell">
        <div className="step-intro">
          <p className="eyebrow">Step 2</p>
          <h1>Inspect what the pipeline actually did.</h1>
          <p>Every duration below is measured during this conversion. The event journal records the source and outcome without replaying simulated work.</p>
        </div>

        <div className="step-card nodes-page-card">
          <div className="conversion-summary">
            <span>Conversion ID</span>
            <strong>{conversion.conversion_id}</strong>
            <p>{conversion.created_at}</p>
            <div className="runtime-total"><Gauge size={15} /> {formatDuration(conversion.runtime?.duration_ms)} total runtime</div>
          </div>
          <div className="conversion-log-panel">
            <div className="terminal-bar"><Terminal size={14} /><span>Conversion event journal</span></div>
            <div className="terminal-body expanded">
              {(conversion.runtime?.events || []).map((event) => (
                <p className="terminal-line" key={event.id}>
                  <time>{new Date(event.timestamp).toLocaleTimeString([], { hour12: false })}</time>
                  <span>{event.metadata?.node_id || event.category}</span>
                  {event.message}
                  {event.duration_ms != null ? ` · ${event.duration_ms} ms` : ""}
                </p>
              ))}
            </div>
          </div>
          <div className="node-grid page-node-grid">
            {conversion.nodes.map((node, index) => (
              <NodeCard node={node} key={node.id} index={index} />
            ))}
          </div>
        </div>

        <div className="step-actions">
          <Link href="/step-1" className="secondary-button">Back to capture</Link>
          <Link href="/step-3" className="primary-button">
            Open browser preview
            <ArrowRight size={18} />
          </Link>
        </div>
      </section>
    </main>
  );
}

function NodeCard({ node, index }) {
  const Icon = nodeIcons[node.id] || Network;
  return (
    <article className="node-card complete phase-card-animated" style={{ animationDelay: `${index * 0.08}s` }}>
      <div>
        <Icon size={18} />
        <small><Sparkles size={11} className="inline-icon" /> {node.status}</small>
      </div>
      <strong>{node.name}</strong>
      <p>{node.detail || node.role}</p>
      <span className="latency">{formatDuration(node.latency_ms)}</span>
    </article>
  );
}

function EmptyStep({ title, text }) {
  return (
    <section className="empty-step">
      <h1>{title}</h1>
      <p>{text}</p>
      <Link href="/step-1" className="primary-button">Go to Step 1</Link>
    </section>
  );
}

function formatDuration(value) {
  if (value == null) return "—";
  return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${Math.round(value)} ms`;
}
