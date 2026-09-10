"""Synthetic business data for reproducible demos and early experiments."""

from __future__ import annotations

import random
from datetime import date, timedelta

from synapse_erp.preprocess import DEFAULT_UNIT, PRICE_BOOK, parse_ledger_line, parse_whatsapp_order
from synapse_erp.schema import LedgerRecord, OrderIntent

CUSTOMERS = ["ramesh", "anita", "salim", "kavya", "mahesh", "walk-in"]
SKU_PHRASES = {
    "sugar": ["sugar", "chini"],
    "rice": ["rice", "chawal"],
    "wheat_flour": ["atta", "flour"],
    "toor_dal": ["toor dal", "dal"],
    "tea": ["tea", "chai"],
    "parle_g": ["parleg", "parle-g"],
    "oil": ["oil", "tel"],
}


def generate_ledger_lines(n: int = 1200, seed: int = 42) -> list[str]:
    rng = random.Random(seed)
    start = date.today() - timedelta(days=160)
    lines: list[str] = []
    skus = list(SKU_PHRASES)
    for idx in range(n):
        sku = rng.choice(skus)
        phrase = rng.choice(SKU_PHRASES[sku])
        unit = DEFAULT_UNIT[sku]
        quantity = rng.choice([1, 2, 3, 5, 10])
        if unit == "pack":
            quantity = rng.choice([1, 2, 5, 10])
        if unit == "l":
            quantity = rng.choice([1, 2, 5])
        amount = round(PRICE_BOOK[sku] * quantity, 2)
        customer = rng.choice(CUSTOMERS)
        day = start + timedelta(days=idx % 160)
        lines.append(f"{day.isoformat()} {customer}: {phrase} {quantity} {unit} Rs {amount}")
    return lines


def generate_ledger_records(n: int = 1200, seed: int = 42) -> list[LedgerRecord]:
    return [parse_ledger_line(line) for line in generate_ledger_lines(n=n, seed=seed)]


def generate_chat_orders(n: int = 40, seed: int = 7) -> list[str]:
    rng = random.Random(seed)
    templates = [
        "{customer}: bhaiya {qty}{unit} {item} bhej do",
        "{customer}: need {qty} {unit} {item} today",
        "{customer}: kal ke liye {qty} {unit} {item}",
        "{customer}: {item} {qty}{unit} pack kar dena",
    ]
    orders: list[str] = []
    for _ in range(n):
        sku = rng.choice(list(SKU_PHRASES))
        orders.append(
            rng.choice(templates).format(
                customer=rng.choice(CUSTOMERS[:-1]),
                qty=rng.choice([1, 2, 3, 5]),
                unit=DEFAULT_UNIT[sku],
                item=rng.choice(SKU_PHRASES[sku]),
            )
        )
    return orders


def generate_order_intents(n: int = 40, seed: int = 7) -> list[OrderIntent]:
    return [parse_whatsapp_order(text) for text in generate_chat_orders(n=n, seed=seed)]


def demand_series_for_sku(sku: str, days: int = 220, seed: int = 99) -> list[float]:
    rng = random.Random(seed + sum(ord(ch) for ch in sku))
    base = PRICE_BOOK.get(sku, 50.0) / 20.0
    series: list[float] = []
    for day in range(days):
        weekly = 1.0 + 0.25 * (day % 7 in {5, 6})
        festival = 1.8 if 90 <= day <= 100 else 1.0
        noise = rng.uniform(-0.8, 0.8)
        value = max(0.0, base * weekly * festival + noise)
        series.append(round(value, 2))
    return series

