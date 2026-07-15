"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Download, Eye, ExternalLink } from "lucide-react";
import { absoluteUrl, getErpOutput, loadConversion } from "../lib/flow";

export default function PreviewPage() {
  const [conversion, setConversion] = useState(null);

  useEffect(() => {
    setConversion(loadConversion());
  }, []);

  const erpOutput = getErpOutput(conversion);

  if (!conversion) {
    return (
      <main className="flow-page">
        <section className="empty-step">
          <h1>No ERP preview yet</h1>
          <p>Run Step 1 first, then this page will show the generated ERP inside a browser viewer.</p>
          <Link href="/step-1" className="primary-button">Go to Step 1</Link>
        </section>
      </main>
    );
  }

  return (
    <main className="flow-page">
      <section className="step-shell">
        <div className="step-intro">
          <p className="eyebrow">Step 3</p>
          <h1>Preview the generated ERP like a browser app.</h1>
          <p>The HTML export still exists, but this page embeds it inside the platform so the output feels like a generated SaaS surface.</p>
        </div>

        <div className="browser-frame full-browser">
          <div className="browser-bar">
            <span />
            <span />
            <span />
            <p>{erpOutput ? absoluteUrl(erpOutput.url) : "No ERP output found"}</p>
          </div>
          {erpOutput ? (
            <iframe src={absoluteUrl(erpOutput.url)} title="Generated ERP preview" />
          ) : (
            <div className="browser-empty">
              <Eye size={30} />
              <strong>No ERP HTML output found.</strong>
            </div>
          )}
        </div>

        <div className="preview-output-grid">
          {conversion.outputs.map((output) => (
            <a href={absoluteUrl(output.url)} target="_blank" rel="noreferrer" key={output.url}>
              <Download size={16} />
              <span>{output.label}</span>
              <small>{output.format}</small>
            </a>
          ))}
        </div>

        <div className="step-actions">
          <Link href="/step-2" className="secondary-button">Back to nodes</Link>
          {erpOutput && (
            <a href={absoluteUrl(erpOutput.url)} target="_blank" rel="noreferrer" className="secondary-button">
              Open raw HTML
              <ExternalLink size={16} />
            </a>
          )}
          <Link href="/step-4" className="primary-button">
            Create CRUD workspace
            <ArrowRight size={18} />
          </Link>
        </div>
      </section>
    </main>
  );
}
