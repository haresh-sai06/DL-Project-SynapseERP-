"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity, BarChart3, Box, Cpu, Download, FileJson, Grid3X3, Home, Menu, Radio, X,
} from "lucide-react";
import { API_BASE } from "../lib/flow";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: Home },
  { href: "/live", label: "Live Dashboard", icon: Radio },
  { href: "/models", label: "Model Hub", icon: Cpu },
  { href: "/step-1", label: "Capture", icon: Box },
  { href: "/step-2", label: "Nodes", icon: Grid3X3 },
  { href: "/step-3", label: "Preview", icon: BarChart3 },
  { href: "/step-4", label: "Workspace", icon: Activity },
  { href: "/final", label: "Outputs", icon: Download },
];

export default function SidebarLayout({ children }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [liveStatus, setLiveStatus] = useState(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    fetch(`${API_BASE}/api/live`)
      .then((r) => r.json())
      .then((d) => setLiveStatus(d.live !== false ? "live" : "cached"))
      .catch(() => setLiveStatus("offline"));
    const t = setInterval(() => {
      fetch(`${API_BASE}/api/live`)
        .then((r) => r.json())
        .then((d) => setLiveStatus(d.live !== false ? "live" : "cached"))
        .catch(() => {});
    }, 30000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="app-shell">
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="sidebar-brand">
          <Link href="/">
            <span className="brand-mark">S</span>
            <span className="brand-text">
              <strong>Synapse ERP</strong>
              <small>offline to SaaS</small>
            </span>
          </Link>
          <button className="sidebar-close" onClick={() => setOpen(false)} aria-label="Close sidebar">
            <X size={18} />
          </button>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== "/" && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={`sidebar-link ${active ? "active" : ""}`}
                onClick={() => setOpen(false)}
              >
                <Icon size={18} />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-status">
            <span className={`pulse ${liveStatus === "live" ? "on" : "off"}`} />
            <span className="sidebar-status-text">
              {liveStatus === "live" ? "Live data" : liveStatus === "cached" ? "Cached" : "Offline"}
            </span>
          </div>
          <small className="sidebar-version">v0.4.0</small>
        </div>
      </aside>

      <div className="sidebar-overlay" onClick={() => setOpen(false)} />

      <div className="main-area">
        <div className="topbar">
          <button className="sidebar-toggle" onClick={() => setOpen(true)} aria-label="Open sidebar">
            <Menu size={20} />
          </button>
          <span className="topbar-path">
            Synapse ERP <span className="topbar-sep">/</span> {NAV_ITEMS.find((i) => pathname === i.href || (i.href !== "/" && pathname.startsWith(i.href)))?.label || "Dashboard"}
          </span>
        </div>
        <div className="page-content">{children}</div>
      </div>
    </div>
  );
}
