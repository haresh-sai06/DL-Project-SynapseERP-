"use client";

import { useEffect, useState } from "react";
import { Radio } from "lucide-react";
import { API_BASE } from "../lib/flow";

export default function LiveTicker() {
  const [data, setData] = useState(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/live`);
        const d = await res.json();
        if (active) setData(d);
      } catch (e) {
        /* ignore */
      }
    };
    load();
    const id = setInterval(load, 15000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const inr = data?.fx?.rates?.INR;
  const btc = data?.crypto?.coins?.[0];

  return (
    <div className="ticker-card">
      <div className="ticker-head">
        <Radio size={14} /> Live feed
        <span className={`pulse ${data?.live === true ? "on" : "off"}`} />
      </div>
      <div className="ticker-row">
        <span>USD → INR</span>
        <strong>{inr != null ? inr.toFixed(2) : "—"}</strong>
      </div>
      <div className="ticker-row">
        <span>BTC / USD</span>
        <strong>{btc?.usd != null ? `$${Number(btc.usd).toLocaleString()}` : "—"}</strong>
      </div>
      <div className="ticker-foot">{data?.live === true ? "live sources" : data ? "cached / unavailable" : "connecting"} · Frankfurter + CoinGecko</div>
    </div>
  );
}
