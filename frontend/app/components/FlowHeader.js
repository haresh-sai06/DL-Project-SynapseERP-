import Link from "next/link";

const steps = [
  ["1", "/step-1", "Capture"],
  ["2", "/step-2", "Nodes"],
  ["3", "/step-3", "Preview"],
  ["4", "/step-4", "Workspace"],
  ["5", "/final", "Outputs"]
];

export default function FlowHeader({ active = "0" }) {
  return (
    <header className="flow-header">
      <Link href="/" className="brand-link">
        <span className="brand-mark">S</span>
        <span>
          <strong>Synapse ERP</strong>
          <small>offline to SaaS converter</small>
        </span>
      </Link>
      <nav className="step-nav">
        <Link className={active === "live" ? "active" : ""} href="/live">
          <span>◎</span>
          Live
        </Link>
        {steps.map(([id, href, label]) => (
          <Link className={active === id ? "active" : ""} href={href} key={id}>
            <span>{id}</span>
            {label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
