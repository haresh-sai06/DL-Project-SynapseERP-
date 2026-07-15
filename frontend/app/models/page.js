"use client";

import { useCallback, useEffect, useState } from "react";
import { Cpu, Download, Eye, TrendingUp, Zap } from "lucide-react";
import Link from "next/link";
import { API_BASE } from "../lib/flow";

export default function ModelsPage() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [training, setTraining] = useState(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/api/models`);
      const d = await r.json();
      setModels(d.models || []);
    } catch (e) {
      setModels([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const runTraining = async (ep, body) => {
    setTraining(ep);
    setResult(null);
    try {
      const r = await fetch(`${API_BASE}${ep}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
      });
      const d = await r.json();
      setResult(d);
      load();
    } catch (e) {
      setResult({ ok: false, error: String(e) });
    } finally {
      setTraining(null);
    }
  };

  const handleInference = async () => {
    try {
      const r = await fetch(`${API_BASE}/api/inference/vision/random`);
      const d = await r.json();
      setResult({ inference: d });
    } catch (e) {
      setResult({ inference: { ok: false, error: String(e) } });
    }
  };

  return (
    <div className="models-page">
      <div className="models-header">
        <div>
          <h1>Model Hub</h1>
          <p className="model-count">{models.length} trained model{models.length !== 1 ? "s" : ""} · real datasets</p>
        </div>
        <div className="gap-row">
          <button
            className="primary-button"
            disabled={training === "/api/train/vision"}
            onClick={() => runTraining("/api/train/vision", { epochs: 3 })}
          >
            {training === "/api/train/vision" ? "Training vision…" : "Train Vision (MNIST)"}
          </button>
          <button
            className="secondary-button"
            disabled={training === "/api/train/forecaster"}
            onClick={() => runTraining("/api/train/forecaster", { epochs: 6, years: 3 })}
          >
            {training === "/api/train/forecaster" ? "Training forecaster…" : "Train Forecaster (FX)"}
          </button>
        </div>
      </div>

      {loading && (
        <div className="model-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="model-card">
              <div className="skeleton skeleton-h2" />
              <div className="skeleton skeleton-p" />
              <div className="skeleton skeleton-card" />
            </div>
          ))}
        </div>
      )}

      {!loading && models.length === 0 && (
        <div className="panel text-center">
          <Cpu size={32} style={{ opacity: 0.4, marginBottom: 8 }} />
          <p>No models trained yet. Click a Train button above to train on real data.</p>
        </div>
      )}

      {models.length > 0 && (
        <div className="model-grid">
          {models.map((m) => (
            <div className="model-card" key={m.name}>
              <h3>{m.name.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}</h3>
              <div className={`model-source ${(m.metrics?.source || "synthetic") === "real" ? "real" : "synthetic"}`}>
                <Zap size={12} /> {(m.metrics?.source || "synthetic") === "real" ? m.metrics.dataset : "synthetic data"}
              </div>

              <div className="model-metrics">
                {Object.entries(m.metrics || {}).filter(([k]) => !["dataset", "source"].includes(k)).slice(0, 8).map(([k, v]) => (
                  <div className="model-metric" key={k}>
                    <em>{k.replace("_", " ")}</em>
                    <strong>{typeof v === "number" ? (v > 1e3 ? v.toLocaleString() : v.toFixed(4)) : String(v)}</strong>
                  </div>
                ))}
              </div>

              {m.loss_curve && (
                <a className="curve-link" href={`${API_BASE}${m.loss_curve}`} target="_blank" rel="noreferrer">
                  <img
                    src={`${API_BASE}${m.loss_curve}`}
                    alt="loss curve"
                    loading="lazy"
                    onError={(e) => { e.target.style.display = "none"; }}
                  />
                </a>
              )}

              <div className="model-actions">
                <a className="btn-sm" href={`${API_BASE}${m.loss_curve}`} target="_blank" rel="noreferrer">
                  <Eye size={14} /> View curve
                </a>
                <a className="btn-sm" href={`${API_BASE}/generated/figures/${m.name}_loss.png`} target="_blank" rel="noreferrer">
                  <Download size={14} /> Download
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {result?.ok && (
        <div className="result-block" style={{ marginTop: 18 }}>
          <h3 style={{ margin: "0 0 10px", fontSize: 15 }}>
            <TrendingUp size={15} /> Training complete — {result.model}
          </h3>
          <div className="metric-chips">
            {Object.entries(result.metrics || {}).filter(([k]) => !["dataset", "source"].includes(k)).map(([k, v]) => (
              <span className="chip" key={k}>
                <em>{k.replace("_", " ")}</em>
                <strong>{typeof v === "number" ? v.toFixed(4) : String(v)}</strong>
              </span>
            ))}
          </div>
        </div>
      )}

      {result?.inference?.ok && (
        <div className="inference-panel">
          <h3><Zap size={15} /> Vision model inference (live)</h3>
          <p>Random MNIST test sample — true: {result.inference.true_label}, predicted: <strong style={{ color: result.inference.correct ? "#34d399" : "#fb7185" }}>{result.inference.predicted_label}</strong> (confidence: {(result.inference.confidence * 100).toFixed(1)}%)</p>
          <pre style={{ fontSize: 11, color: "var(--muted)", margin: 0 }}>
            Correct: {result.inference.correct ? "YES ✓" : "NO ✗"} · Sample index: {result.inference.sample_index}
          </pre>
        </div>
      )}
      {result?.inference && !result.inference?.ok && (
        <div className="chart-empty">Inference not available: {result.inference.error}</div>
      )}

      <div style={{ marginTop: 18 }} className="gap-row">
        <button className="secondary-button" onClick={handleInference}>
          <Zap size={15} /> Test Vision Inference (random sample)
        </button>
        <Link href="/live" className="btn-sm">See live data dashboard →</Link>
      </div>
    </div>
  );
}
