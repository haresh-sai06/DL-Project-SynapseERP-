"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Activity, Cpu, LineChart as LineIcon, Radio, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";
import LineChart from "../components/LineChart";
import { API_BASE } from "../lib/flow";

const FX_HIGHLIGHTS = ["INR", "EUR", "GBP", "JPY", "CNY", "AED", "SGD", "ZAR"];

export default function LivePage() {
  const [snapshot, setSnapshot] = useState(null);
  const [history, setHistory] = useState([]);
  const [years, setYears] = useState(3);
  const [models, setModels] = useState([]);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [training, setTraining] = useState(null);
  const [result, setResult] = useState(null);
  const timer = useRef(null);

  const loadLive = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/live`);
      const data = await res.json();
      setSnapshot(data);
      setUpdatedAt(new Date());
    } catch (e) {
      /* keep previous snapshot on transient failure */
    }
  }, []);

  const loadHistory = useCallback(async (y) => {
    try {
      const res = await fetch(`${API_BASE}/api/live/history?base=USD&symbol=INR&years=${y}`);
      const data = await res.json();
      setHistory(data.series || []);
    } catch (e) {
      setHistory([]);
    }
  }, []);

  const loadModels = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/models`);
      const data = await res.json();
      setModels(data.models || []);
    } catch (e) {
      setModels([]);
    }
  }, []);

  useEffect(() => {
    loadLive();
    loadHistory(years);
    loadModels();
    timer.current = setInterval(loadLive, 15000);
    return () => clearInterval(timer.current);
  }, [loadLive, loadHistory, loadModels, years]);

  const runTraining = async (endpoint, payload) => {
    setTraining(endpoint);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload || {}),
      });
      const data = await res.json();
      setResult(data);
      loadModels();
    } catch (e) {
      setResult({ ok: false, error: String(e) });
    } finally {
      setTraining(null);
    }
  };

  const fx = snapshot?.fx?.rates || {};
  const crypto = snapshot?.crypto?.coins || [];
  const commodities = snapshot?.commodities?.commodities || [];
  const isLive = snapshot?.live !== false;

  return (
    <main className="live-page">
      <section className="live-hero">
        <div>
          <p className="eyebrow">
            <Radio size={15} /> Real-time intelligence
          </p>
          <h1>
            Live market signals <span className="gradient-text">&amp; real model training</span>
          </h1>
          <p>
            Live FX, precious metals, and crypto prices from public APIs with real deep-learning
            model training on real datasets. No mocked numbers.
          </p>
        </div>
        <div className="live-status">
          <span className={`pulse ${isLive ? "on" : "off"}`} />
          <div>
            <strong>{isLive ? "Live feed connected" : "Cached (offline)"}</strong>
            <small>
              {updatedAt ? `updated ${updatedAt.toLocaleTimeString()}` : "connecting…"} · auto-refresh 15s
            </small>
          </div>
          <button className="ghost-btn" onClick={loadLive}>
            <RefreshCw size={15} /> Refresh
          </button>
        </div>
      </section>

      <section className="stat-grid">
        <StatCard icon={<TrendingUp size={18} />} label="USD → INR (live)" value={fmt(fx.INR)} hint="ECB reference" />
        <StatCard
          icon={<Activity size={18} />}
          label="BTC (USD, live)"
          value={fmt(crypto[0]?.usd, "$")}
          hint={`${pct(crypto[0]?.change_24h)} 24h`}
          trend={crypto[0]?.change_24h}
        />
        <StatCard icon={<Radio size={18} />} label="Data sources" value="3 live" hint="ECB · CoinGecko · GoldAPI" />
        <StatCard
          icon={<Cpu size={18} />}
          label="Trained models"
          value={models.length}
          hint="real datasets"
        />
      </section>

      <section className="live-grid">
        <div className="panel">
          <div className="panel-head">
            <h2>
              <TrendingUp size={16} /> Live FX rates
            </h2>
            <span className="panel-sub">{snapshot?.fx?.source}</span>
          </div>
          <div className="rate-table">
            {FX_HIGHLIGHTS.map((code) =>
              fx[code] != null ? (
                <div className="rate-row" key={code}>
                  <span className="rate-code">1 USD =</span>
                  <span className="rate-value">{fx[code].toFixed(3)}</span>
                  <span className="rate-unit">{code}</span>
                </div>
              ) : null
            )}
          </div>

          <div className="panel-head" style={{ marginTop: 22 }}>
            <h2>
              <TrendingUp size={16} /> Crypto spot (USD)
            </h2>
          </div>
          <div className="coin-grid">
            {crypto.map((c) => (
              <div className="coin-card" key={c.id}>
                <div className="coin-top">
                  <span className="coin-sym">{c.symbol.toUpperCase()}</span>
                  <span className={`pill ${c.change_24h >= 0 ? "up" : "down"}`}>
                    {c.change_24h >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                    {pct(c.change_24h)}
                  </span>
                </div>
                <div className="coin-price">${fmt(c.usd)}</div>
                <div className="coin-inr">₹ {fmt(c.inr)}</div>
              </div>
            ))}
            {crypto.length === 0 && <div className="chart-empty">No crypto data right now.</div>}
          </div>

          <div className="panel-head" style={{ marginTop: 22 }}>
            <h2>
              <TrendingUp size={16} /> Precious metals (USD)
            </h2>
          </div>
          <div className="commodity-grid">
            {commodities.map((c) => (
              <div className="commodity-card" key={c.symbol}>
                <div className="comm-code">{c.symbol}</div>
                <div className="comm-price">{c.name === "Gold" ? `$${Number(c.price_usd).toLocaleString()}` : fmt(c.price_usd, "$")}</div>
                <div className="comm-change up">· {c.name}</div>
              </div>
            ))}
            {commodities.length === 0 && <div className="chart-empty">No commodity data right now.</div>}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>
              <LineIcon size={16} /> USD → INR history (real)
            </h2>
            <div className="year-switch">
              {[1, 2, 3, 5].map((y) => (
                <button
                  key={y}
                  className={years === y ? "active" : ""}
                  onClick={() => {
                    setYears(y);
                    loadHistory(y);
                  }}
                >
                  {y}y
                </button>
              ))}
            </div>
          </div>
          <LineChart data={history} label="USD to INR daily rate" height={240} />
          <p className="panel-note">
            {history.length} real daily observations from the Frankfurter / ECB dataset. This is the
            series the demand forecaster trains on.
          </p>
        </div>
      </section>

      <section className="panel train-panel">
        <div className="panel-head">
          <h2>
            <Cpu size={16} /> Real deep-learning training
          </h2>
          <span className="panel-sub">weights updated on labeled loss</span>
        </div>
        <div className="train-grid">
          <div className="train-card">
            <h3>Vision encoder · real MNIST</h3>
            <p>Convolutional CNN trained on 60k real handwritten digit images.</p>
            <button
              className="primary-button train-btn"
              disabled={training === "/api/train/vision"}
              onClick={() => runTraining("/api/train/vision", { epochs: 3 })}
            >
              {training === "/api/train/vision" ? <Spinner /> : "Train on real MNIST"}
            </button>
          </div>
          <div className="train-card">
            <h3>Demand forecaster · real FX</h3>
            <p>LSTM trained on real USD/INR import-cost series vs a moving-average baseline.</p>
            <button
              className="primary-button train-btn"
              disabled={training === "/api/train/forecaster"}
              onClick={() => runTraining("/api/train/forecaster", { epochs: 6, years: 3 })}
            >
              {training === "/api/train/forecaster" ? <Spinner /> : "Train on real FX"}
            </button>
          </div>
        </div>

        {result?.ok && (
          <div className="result-block">
            <div className="metric-chips">
              {Object.entries(result.metrics || {}).map(([k, v]) => (
                <span className="chip" key={k}>
                  <em>{k}</em>
                  <strong>{typeof v === "number" ? v.toFixed(4) : String(v)}</strong>
                </span>
              ))}
            </div>
            {result.loss_curve && (
              <a className="curve-link" href={`${API_BASE}${result.loss_curve}`} target="_blank" rel="noreferrer">
                <img src={`${API_BASE}${result.loss_curve}`} alt="training loss curve" />
                View loss curve
              </a>
            )}
          </div>
        )}
        {result && !result.ok && <div className="chart-empty">Training failed: {result.error}</div>}

        {models.length > 0 && (
          <div className="model-list">
            {models.map((m) => (
              <div className="model-row" key={m.name}>
                <span>
                  <strong>{m.name}</strong> · {m.metrics?.dataset || "trained"}
                </span>
                <a href={`${API_BASE}${m.loss_curve}`} target="_blank" rel="noreferrer">
                  loss curve ↗
                </a>
              </div>
            ))}
          </div>
        )}
        <div className="gap-row mt-16">
          <Link href="/models" className="btn-sm"><Cpu size={14} /> Full model hub</Link>
          <button className="btn-sm" onClick={async () => {
            try {
              const r = await fetch(`${API_BASE}/api/inference/vision/random`);
              const d = await r.json();
              setResult({ inference: d });
            } catch (e) {
              setResult({ inference: { ok: false, error: String(e) } });
            }
          }}>
            Test live inference →
          </button>
        </div>
        {result?.inference?.ok && (
          <div className="inference-panel" style={{ marginTop: 12 }}>
            <h3 style={{ margin: 0 }}>Model inference result</h3>
            <p style={{ margin: "8px 0 0" }}>
              Real MNIST sample: true digit <strong>{result.inference.true_label}</strong>, predicted <strong style={{ color: result.inference.correct ? "#34d399" : "#fb7185" }}>{result.inference.predicted_label}</strong> · confidence {(result.inference.confidence * 100).toFixed(1)}% — {result.inference.correct ? "CORRECT ✓" : "WRONG ✗"}
            </p>
          </div>
        )}
      </section>

      <footer className="live-footer">
        <span>Built on public data · Frankfurter (ECB) · CoinGecko · GoldAPI</span>
        <div className="gap-row">
          <Link href="/models">Model Hub →</Link>
          <Link href="/step-1">Start a conversion →</Link>
        </div>
      </footer>
    </main>
  );
}

function StatCard({ icon, label, value, hint, trend }) {
  return (
    <div className="stat-card">
      <div className="stat-icon">{icon}</div>
      <div>
        <div className="stat-label">{label}</div>
        <div className={`stat-value ${trend != null ? (trend >= 0 ? "pos" : "neg") : ""}`}>{value}</div>
        <div className="stat-hint">{hint}</div>
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <span className="spinner" aria-label="training">
      training…
    </span>
  );
}

function fmt(v, prefix = "") {
  if (v == null) return "—";
  return prefix + Number(v).toLocaleString("en-US", { maximumFractionDigits: 2 });
}

function pct(v) {
  if (v == null) return "0.0%";
  return `${v >= 0 ? "+" : ""}${Number(v).toFixed(2)}%`;
}
