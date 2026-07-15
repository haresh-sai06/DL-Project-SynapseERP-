"""Typed records shared by the ingestion, graph, and ERP layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class LedgerRecord:
    date: str
    item: str
    quantity: float
    unit: str
    amount: float
    customer: str = "walk-in"
    source: str = "ledger"


@dataclass(frozen=True)
class OrderIntent:
    customer: str
    item: str
    quantity: float
    unit: str
    raw_text: str
    source: str = "whatsapp"


@dataclass(frozen=True)
class InventoryItem:
    sku: str
    display_name: str
    unit: str
    quantity_sold: float
    revenue: float
    reorder_hint: float


@dataclass(frozen=True)
class CustomerProfile:
    name: str
    orders: int
    revenue: float
    last_item: str
    credit_risk: str = "unknown"


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    customer: str
    item: str
    quantity: float
    unit: str
    amount: float


@dataclass(frozen=True)
class AnalyticsSummary:
    total_revenue: float
    total_orders: int
    top_sku: str
    forecast_message: str
    anomaly_message: str


@dataclass(frozen=True)
class BusinessSnapshot:
    inventory: list[InventoryItem] = field(default_factory=list)
    customers: list[CustomerProfile] = field(default_factory=list)
    invoices: list[Invoice] = field(default_factory=list)
    analytics: AnalyticsSummary | None = None
    source_records: list[LedgerRecord] = field(default_factory=list)
    source_orders: list[OrderIntent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

