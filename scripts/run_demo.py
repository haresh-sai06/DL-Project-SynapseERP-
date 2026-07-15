"""Generate a complete static ERP demo from synthetic shop records."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from synapse_erp.data.synthetic import generate_chat_orders, generate_ledger_lines  # noqa: E402
from synapse_erp.erp import render_erp_html  # noqa: E402
from synapse_erp.pipeline import SynapseERPPipeline  # noqa: E402


def main() -> None:
    demo_dir = PROJECT_ROOT / "data" / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    ledger_lines = generate_ledger_lines(n=75)
    chat_lines = generate_chat_orders(n=12)
    (demo_dir / "ledger_lines.txt").write_text("\n".join(ledger_lines), encoding="utf-8")
    (demo_dir / "whatsapp_orders.txt").write_text("\n".join(chat_lines), encoding="utf-8")

    snapshot = SynapseERPPipeline().ingest(ledger_lines=ledger_lines, chat_lines=chat_lines)
    erp_path = render_erp_html(snapshot)
    summary = {
        "erp_path": str(erp_path),
        "ledger_records": len(snapshot.source_records),
        "chat_orders": len(snapshot.source_orders),
        "inventory_items": len(snapshot.inventory),
        "customers": len(snapshot.customers),
        "total_revenue": snapshot.analytics.total_revenue if snapshot.analytics else 0,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

