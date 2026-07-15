"""Streamlit front end for the Synapse ERP demo."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import streamlit as st  # noqa: E402

from synapse_erp.erp import render_erp_html  # noqa: E402
from synapse_erp.pipeline import SynapseERPPipeline  # noqa: E402


st.set_page_config(page_title="Synapse ERP", layout="wide")
st.title("Synapse ERP")
st.caption("Ingest ledger lines and chat orders, then generate inventory, CRM, invoices, and analytics.")

default_ledger = """2026-06-01 ramesh: chini 2 kg Rs 88
2026-06-01 anita: rice 5 kg Rs 310
2026-06-02 salim: parle-g 10 pack Rs 100"""
default_chat = """kavya: bhaiya 2kg atta bhej do
mahesh: need 1 l oil today"""

left, right = st.columns(2)
with left:
    ledger_text = st.text_area("Ledger OCR text", value=default_ledger, height=180)
with right:
    chat_text = st.text_area("WhatsApp orders", value=default_chat, height=180)

if st.button("Generate ERP", type="primary"):
    snapshot = SynapseERPPipeline().ingest(
        ledger_lines=ledger_text.splitlines(),
        chat_lines=chat_text.splitlines(),
    )
    html_path = render_erp_html(snapshot)
    st.success(f"ERP generated: {html_path}")
    st.metric("Revenue", f"Rs {snapshot.analytics.total_revenue:,.2f}" if snapshot.analytics else "Rs 0")
    st.metric("Orders", snapshot.analytics.total_orders if snapshot.analytics else 0)
    st.metric("Top SKU", snapshot.analytics.top_sku if snapshot.analytics else "none")
    st.dataframe([item.__dict__ for item in snapshot.inventory], use_container_width=True)
    st.dataframe([customer.__dict__ for customer in snapshot.customers], use_container_width=True)

