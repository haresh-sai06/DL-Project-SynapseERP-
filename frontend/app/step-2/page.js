"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Boxes, BrainCircuit, Camera, ClipboardList, Download, LineChart, Network, ReceiptText, UploadCloud } from "lucide-react";
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
          <h1>Watch the backend conversion graph.</h1>
          <p>Each service runs as a visible node: upload, preprocessing, OCR, product vision, order NER, graph, forecast, ERP, and export.</p>
        </div>

        <div className="step-card nodes-page-card">
          <div className="conversion-summary">
            <span>Conversion ID</span>
            <strong>{conversion.conversion_id}</strong>
            <p>{conversion.created_at}</p>
          </div>
          <div className="node-grid page-node-grid">
            {conversion.nodes.map((node) => <NodeCard node={node} key={node.id} />)}
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

function NodeCard({ node }) {
  const Icon = nodeIcons[node.id] || Network;
  return (
    <article className="node-card complete">
      <div>
        <Icon size={18} />
        <small>{node.status}</small>
      </div>
      <strong>{node.name}</strong>
      <p>{node.detail || node.role}</p>
      {node.latency_ms ? <span className="latency">{node.latency_ms} ms</span> : null}
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
