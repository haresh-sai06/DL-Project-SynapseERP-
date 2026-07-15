"""Run the current Synapse ERP ingestion demo and print a compact summary."""

from __future__ import annotations

import json

from synapse_erp.erp import render_erp_html
from synapse_erp.pipeline import SynapseERPPipeline


def main() -> None:
    snapshot = SynapseERPPipeline().ingest()
    html_path = render_erp_html(snapshot)
    summary = {
        "erp_path": str(html_path),
        "total_revenue": snapshot.analytics.total_revenue if snapshot.analytics else 0,
        "total_orders": snapshot.analytics.total_orders if snapshot.analytics else 0,
        "top_sku": snapshot.analytics.top_sku if snapshot.analytics else "none",
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

