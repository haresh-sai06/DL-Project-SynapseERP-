"""End-to-end orchestration from messy inputs to a structured business snapshot."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from synapse_erp.preprocess import DEFAULT_UNIT, display_name, parse_ledger_line, parse_whatsapp_order
from synapse_erp.schema import (
    AnalyticsSummary,
    BusinessSnapshot,
    CustomerProfile,
    InventoryItem,
    Invoice,
    LedgerRecord,
    OrderIntent,
)


class BusinessKnowledgeGraph:
    """Small in-memory graph that links ledgers, orders, SKUs, and customers."""

    def build(self, records: list[LedgerRecord], orders: list[OrderIntent]) -> BusinessSnapshot:
        revenue_by_sku: dict[str, float] = defaultdict(float)
        qty_by_sku: dict[str, float] = defaultdict(float)
        unit_by_sku: dict[str, str] = {}
        customer_revenue: dict[str, float] = defaultdict(float)
        customer_orders: dict[str, int] = defaultdict(int)
        customer_last_item: dict[str, str] = {}
        invoices: list[Invoice] = []

        for record in records:
            revenue_by_sku[record.item] += record.amount
            qty_by_sku[record.item] += record.quantity
            unit_by_sku[record.item] = record.unit
            customer_revenue[record.customer] += record.amount
            customer_orders[record.customer] += 1
            customer_last_item[record.customer] = record.item

        for index, order in enumerate(orders, start=1):
            priced_amount = order.amount if order.amount is not None else 0.0
            revenue_by_sku[order.item] += priced_amount
            qty_by_sku[order.item] += order.quantity
            unit_by_sku[order.item] = order.unit
            customer_revenue[order.customer] += priced_amount
            customer_orders[order.customer] += 1
            customer_last_item[order.customer] = order.item
            invoices.append(
                Invoice(
                    invoice_id=f"INV-{index:04d}",
                    customer=order.customer,
                    item=order.item,
                    quantity=order.quantity,
                    unit=order.unit,
                    amount=order.amount,
                )
            )

        inventory = [
            InventoryItem(
                sku=sku,
                display_name=display_name(sku),
                unit=unit_by_sku.get(sku, DEFAULT_UNIT.get(sku, "unit")),
                quantity_sold=round(qty_by_sku[sku], 2),
                revenue=round(revenue_by_sku[sku], 2),
                reorder_hint=round(max(1.0, qty_by_sku[sku] / 20.0), 2),
            )
            for sku in sorted(qty_by_sku, key=lambda item: revenue_by_sku[item], reverse=True)
        ]

        customers = [
            CustomerProfile(
                name=name,
                orders=customer_orders[name],
                revenue=round(customer_revenue[name], 2),
                last_item=display_name(customer_last_item.get(name, "unknown")),
                credit_risk=self._risk_bucket(customer_revenue[name], customer_orders[name]),
            )
            for name in sorted(customer_orders, key=lambda item: customer_revenue[item], reverse=True)
        ]

        top_sku = inventory[0].display_name if inventory else "none"
        total_revenue = round(sum(revenue_by_sku.values()), 2)
        total_orders = len(records) + len(orders)
        forecast_message = self._forecast_message(inventory)
        anomaly_message = self._anomaly_message(records)

        return BusinessSnapshot(
            inventory=inventory,
            customers=customers,
            invoices=invoices,
            analytics=AnalyticsSummary(
                total_revenue=total_revenue,
                total_orders=total_orders,
                top_sku=top_sku,
                forecast_message=forecast_message,
                anomaly_message=anomaly_message,
            ),
            source_records=records,
            source_orders=orders,
        )

    @staticmethod
    def _risk_bucket(revenue: float, orders: int) -> str:
        average = revenue / max(orders, 1)
        if orders >= 10 and average > 300:
            return "watch credit"
        if orders >= 4:
            return "healthy"
        return "new"

    @staticmethod
    def _forecast_message(inventory: list[InventoryItem]) -> str:
        if not inventory:
            return "No demand yet."
        item = inventory[0]
        return f"Restock about {item.reorder_hint:g} {item.unit} of {item.display_name} next week."

    @staticmethod
    def _anomaly_message(records: list[LedgerRecord]) -> str:
        high_values = [record for record in records if record.amount > 1000]
        if high_values:
            return f"{len(high_values)} unusually high ledger entries need review."
        return "No high-value anomalies in the submitted ledger."


class SynapseERPPipeline:
    """Offline-to-ERP pipeline over submitted or model-extracted records."""

    def __init__(self) -> None:
        self.graph = BusinessKnowledgeGraph()

    def ingest(
        self,
        ledger_lines: list[str] | None = None,
        chat_lines: list[str] | None = None,
    ) -> BusinessSnapshot:
        ledger_lines = ledger_lines or []
        chat_lines = chat_lines or []
        records = [parse_ledger_line(line) for line in ledger_lines if line.strip()]
        orders = [parse_whatsapp_order(line) for line in chat_lines if line.strip()]
        return self.graph.build(records=records, orders=orders)

    def ingest_files(self, ledger_path: Path, chat_path: Path) -> BusinessSnapshot:
        ledger_lines = ledger_path.read_text(encoding="utf-8").splitlines()
        chat_lines = chat_path.read_text(encoding="utf-8").splitlines()
        return self.ingest(ledger_lines=ledger_lines, chat_lines=chat_lines)
