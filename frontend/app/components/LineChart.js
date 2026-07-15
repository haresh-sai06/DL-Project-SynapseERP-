"use client";

import { useMemo } from "react";

/**
 * Lightweight, dependency-free SVG line/area chart inspired by premium admin
 * templates (TailAdmin / Aceternity style). Pure SVG so it works offline.
 */
export default function LineChart({
  data = [],
  height = 240,
  stroke = "#7fe3b4",
  fillFrom = "rgba(127,227,180,0.28)",
  fillTo = "rgba(127,227,180,0.0)",
  label = "",
}) {
  const { path, area, min, max, last, points } = useMemo(() => {
    if (!data.length) return { path: "", area: "", min: 0, max: 0, last: 0, points: [] };
    const values = data.map((d) => (typeof d === "number" ? d : d.value));
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const w = 1000;
    const h = 320;
    const pts = values.map((v, i) => {
      const x = (i / Math.max(values.length - 1, 1)) * w;
      const y = h - ((v - min) / span) * (h - 40) - 20;
      return [x, y];
    });
    const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
    const areaPath =
      `M0,${h} ` + pts.map((p) => `L${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ") + ` L${w},${h} Z`;
    return { path: line, area: areaPath, min, max, last: values[values.length - 1], points: pts };
  }, [data]);

  const gid = useMemo(() => `grad-${Math.random().toString(36).slice(2, 9)}`, []);

  if (!data.length) {
    return <div className="chart-empty">No data yet</div>;
  }

  return (
    <div className="chart-wrap" style={{ height }}>
      <svg viewBox="0 0 1000 320" preserveAspectRatio="none" className="chart-svg" role="img" aria-label={label}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={fillFrom} />
            <stop offset="100%" stopColor={fillTo} />
          </linearGradient>
        </defs>
        <path d={area} fill={`url(#${gid})`} />
        <path d={path} fill="none" stroke={stroke} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={points[points.length - 1]?.[0]} cy={points[points.length - 1]?.[1]} r="5" fill={stroke} />
      </svg>
      <div className="chart-meta">
        <span>
          low <strong>{min.toFixed(2)}</strong>
        </span>
        <span>
          high <strong>{max.toFixed(2)}</strong>
        </span>
        <span>
          last <strong>{last.toFixed(2)}</strong>
        </span>
      </div>
    </div>
  );
}
