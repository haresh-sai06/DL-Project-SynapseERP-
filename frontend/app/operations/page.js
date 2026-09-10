"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  Gauge,
  RefreshCw,
  Server,
  Terminal
} from "lucide-react";
import { API_BASE } from "../lib/flow";

export default function OperationsPage() {
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/observability?limit=100`, { cache: "no-store" });
      if (!response.ok) throw new Error("The observability endpoint is unavailable.");
      setSnapshot(await response.json());
      setError("");
    } catch (requestError) {
      setError(requestError.message || "Could not load runtime telemetry.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  const metrics = snapshot?.metrics || {};
  const jobs = snapshot?.jobs || {};
  const events = [...(snapshot?.events || [])].reverse();
  const healthy = !error && snapshot?.status === "operational";

  return (
    <main className="operations-page">
      <section className="ops-header">
        <div>
          <p className="eyebrow"><Activity size={15} /> Runtime observability</p>
          <h1>Operations &amp; benchmarks</h1>
          <p>Measured API latency, conversion outcomes, source provenance, and the exact event trail written by the running backend.</p>
        </div>
        <div className={`ops-health ${healthy ? "healthy" : "degraded"}`}>
          {healthy ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
          <div>
            <strong>{healthy ? "Backend operational" : "Backend unavailable"}</strong>
            <small>{snapshot ? `uptime ${formatUptime(snapshot.uptime_seconds)}` : "waiting for telemetry"}</small>
          </div>
          <button className="ghost-btn" onClick={load} disabled={loading} aria-label="Refresh telemetry">
            <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh
          </button>
        </div>
      </section>

      {error && <div className="ops-alert"><AlertTriangle size={17} /> {error}</div>}

      <section className="ops-metric-grid" aria-label="Runtime benchmarks">
        <Metric icon={Gauge} label="Average API latency" value={formatMs(metrics.average_latency_ms)} hint="measured response time" />
        <Metric icon={Clock3} label="P95 API latency" value={formatMs(metrics.p95_latency_ms)} hint="slowest 5% threshold" />
        <Metric icon={AlertTriangle} label="Server error rate" value={formatPercent(metrics.error_rate)} hint={`${metrics.errors || 0} errors observed`} tone={(metrics.error_rate || 0) > 0 ? "warn" : "good"} />
        <Metric icon={Server} label="Requests observed" value={metrics.requests ?? "—"} hint="current process window" />
        <Metric icon={CheckCircle2} label="Conversions complete" value={jobs.completed ?? metrics.completed_conversions ?? "—"} hint={`${jobs.running || 0} running · ${jobs.failed || 0} failed`} />
      </section>

      <section className="ops-grid">
        <article className="ops-panel">
          <div className="panel-head">
            <h2><Database size={17} /> Data-source contract</h2>
            <span className="panel-sub">no fabricated fallback values</span>
          </div>
          <div className="source-list">
            {(snapshot?.sources || []).map((source) => (
              <div className="source-row" key={source.name}>
                <span className="source-icon"><Database size={15} /></span>
                <div><strong>{source.name}</strong><small>{source.kind}</small></div>
                <span className="source-refresh">{source.refresh_seconds ? `TTL ${source.refresh_seconds}s` : "event-driven"}</span>
              </div>
            ))}
            {!snapshot && <div className="skeleton skeleton-card" />}
          </div>
        </article>

        <article className="ops-panel ops-log-panel">
          <div className="panel-head">
            <h2><Terminal size={17} /> Live event journal</h2>
            <span className="panel-sub">refreshes every 5 seconds</span>
          </div>
          <div className="ops-log" aria-live="polite">
            {events.map((event) => (
              <div className={`ops-event ${event.level === "error" ? "event-error" : ""}`} key={event.id}>
                <time>{formatDate(event.timestamp)}</time>
                <span className="event-category">{event.category}</span>
                <p>{event.message}</p>
                <strong>{event.duration_ms != null ? formatMs(event.duration_ms) : "—"}</strong>
              </div>
            ))}
            {!loading && events.length === 0 && <div className="ops-empty">No runtime events have been recorded yet.</div>}
          </div>
        </article>
      </section>
    </main>
  );
}

function Metric({ icon: Icon, label, value, hint, tone = "" }) {
  return (
    <article className={`ops-metric ${tone}`}>
      <span className="ops-metric-icon"><Icon size={18} /></span>
      <div><span>{label}</span><strong>{value}</strong><small>{hint}</small></div>
    </article>
  );
}

function formatMs(value) {
  if (value == null) return "—";
  return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${Number(value).toFixed(1)} ms`;
}

function formatPercent(value) {
  if (value == null) return "—";
  return `${(Number(value) * 100).toFixed(2)}%`;
}

function formatUptime(seconds = 0) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function formatDate(value) {
  return new Date(value).toLocaleTimeString([], { hour12: false });
}
