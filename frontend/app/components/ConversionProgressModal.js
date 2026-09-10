"use client";

import { useEffect, useRef, useState } from "react";
import {
  Boxes,
  Camera,
  CheckCircle2,
  ClipboardList,
  Download,
  FileSearch,
  Loader2,
  Network,
  ReceiptText,
  ShieldCheck,
  Terminal,
  TrendingUp,
  XCircle
} from "lucide-react";
import { API_BASE } from "../lib/flow";

export const PIPELINE_PHASES = [
  { id: "gateway", name: "Input verification", role: "Validate submitted records and uploads", icon: ShieldCheck },
  { id: "preprocess", name: "Asset profiling", role: "Checksum and inspect submitted images", icon: Camera },
  { id: "ledger_ocr", name: "Ledger extraction", role: "Use supplied text or run the local CRNN", icon: ClipboardList },
  { id: "product_vision", name: "Product catalog", role: "Record labels with explicit provenance", icon: Boxes },
  { id: "order_ner", name: "Order parsing", role: "Normalize submitted chat order lines", icon: FileSearch },
  { id: "graph", name: "Business graph", role: "Link customers, SKUs, and transactions", icon: Network },
  { id: "forecast", name: "Demand signal", role: "Calculate transparent velocity heuristics", icon: TrendingUp },
  { id: "erp", name: "ERP workspace", role: "Render the conversion snapshot", icon: ReceiptText },
  { id: "export", name: "Artifact export", role: "Write JSON, CSV, report, and HTML", icon: Download }
];

export default function ConversionProgressModal({ active, jobId, onComplete, onDismiss, error }) {
  const [job, setJob] = useState(null);
  const [pollError, setPollError] = useState("");
  const completedRef = useRef(false);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    if (!active || !jobId) {
      setJob(null);
      setPollError("");
      completedRef.current = false;
      return;
    }

    let cancelled = false;
    let timer;
    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/conversions/${jobId}`, { cache: "no-store" });
        if (!response.ok) throw new Error(await response.text());
        const nextJob = await response.json();
        if (cancelled) return;
        setJob(nextJob);
        setPollError("");
        if (nextJob.status === "completed" && nextJob.result && !completedRef.current) {
          completedRef.current = true;
          window.setTimeout(() => onCompleteRef.current?.(nextJob.result), 450);
          return;
        }
        if (nextJob.status !== "failed") timer = window.setTimeout(poll, 600);
      } catch (requestError) {
        if (cancelled) return;
        setPollError(requestError.message || "Could not read conversion progress.");
        timer = window.setTimeout(poll, 1400);
      }
    };
    poll();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [active, jobId]);

  if (!active) return null;

  const failed = job?.status === "failed";
  const done = job?.status === "completed";
  const progress = job?.progress || 0;
  const completedNodes = Object.values(job?.nodes || {}).filter((node) => node.status === "completed").length;
  const events = job?.events || [];
  const visibleError = error || job?.error || pollError;

  return (
    <div className="progress-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="conversion-title">
      <div className="progress-modal-card">
        <div className="progress-modal-header">
          <div className="modal-title-group">
            <span className="pulse-icon">
              {failed ? <XCircle size={24} className="text-coral" /> : done ? <CheckCircle2 size={24} className="text-mint" /> : <Loader2 size={24} className="spin text-mint" />}
            </span>
            <div>
              <h3 id="conversion-title">{failed ? "Conversion needs attention" : done ? "Conversion complete" : "Processing submitted records"}</h3>
              <p>{jobId ? `Job ${jobId}` : "Creating a conversion job…"}</p>
            </div>
          </div>
          <div className="modal-badge-group">
            <span className="progress-percentage">{progress}%</span>
            <span className="node-count-badge">{completedNodes} / {PIPELINE_PHASES.length} measured</span>
          </div>
        </div>

        <div className="progress-track-container" aria-label="Conversion progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow={progress} role="progressbar">
          <div className="progress-track-fill" style={{ width: `${progress}%` }} />
        </div>

        <div className="phase-stepper-grid">
          {PIPELINE_PHASES.map((phase) => {
            const Icon = phase.icon;
            const node = job?.nodes?.[phase.id];
            const status = node?.status || "pending";
            return (
              <div key={phase.id} className={`phase-step-item ${status}`}>
                <div className="phase-icon-wrapper"><Icon size={16} /></div>
                <div className="phase-info">
                  <strong>{phase.name}</strong>
                  <small>{node?.message || phase.role}</small>
                </div>
                <div className="phase-status-tag">
                  {status === "completed" && <span className="tag-completed">Done · {formatDuration(node.duration_ms)}</span>}
                  {status === "running" && <span className="tag-running"><Loader2 size={11} className="spin" /> Running</span>}
                  {status === "failed" && <span className="tag-failed">Failed</span>}
                  {status === "pending" && <span className="tag-pending">Queued</span>}
                </div>
              </div>
            );
          })}
        </div>

        <div className="pipeline-terminal">
          <div className="terminal-bar">
            <Terminal size={14} />
            <span>Measured runtime events</span>
            {!failed && !done && <span className="terminal-dot pulse-dot" />}
          </div>
          <div className="terminal-body" aria-live="polite">
            {events.length === 0 && <p className="terminal-line muted">Waiting for the worker…</p>}
            {events.map((event) => (
              <p key={event.id} className={`terminal-line ${event.level === "error" ? "error-line" : ""}`}>
                <time>{formatTime(event.timestamp)}</time>
                <span>{event.category}</span>
                {event.message}
                {event.duration_ms != null ? ` · ${event.duration_ms} ms` : ""}
              </p>
            ))}
          </div>
        </div>

        {visibleError && <div className="modal-error-banner">{visibleError}</div>}
        {failed && (
          <button className="secondary-button modal-dismiss" type="button" onClick={onDismiss}>
            Return to source records
          </button>
        )}
      </div>
    </div>
  );
}

function formatTime(value) {
  if (!value) return "--:--:--";
  return new Date(value).toLocaleTimeString([], { hour12: false });
}

function formatDuration(value) {
  if (value == null) return "—";
  if (value > 0 && value < 1) return "<1 ms";
  return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${Math.round(value)} ms`;
}
