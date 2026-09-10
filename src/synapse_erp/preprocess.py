"""Preprocessing helpers for ledger lines, chat orders, and SKU aliases."""

from __future__ import annotations

import re
from datetime import datetime

from synapse_erp.schema import LedgerRecord, OrderIntent

SKU_ALIASES = {
    "sugar": {"sugar", "chini", "sakkar"},
    "rice": {"rice", "chawal", "arisi"},
    "wheat_flour": {"atta", "flour", "aata"},
    "toor_dal": {"dal", "toor", "arhar", "paruppu"},
    "tea": {"tea", "chai"},
    "parle_g": {"parleg", "parle-g", "parle", "biscuit"},
    "oil": {"oil", "tel", "ennai"},
}

DISPLAY_NAMES = {
    "sugar": "Sugar",
    "rice": "Rice",
    "wheat_flour": "Wheat flour",
    "toor_dal": "Toor dal",
    "tea": "Tea",
    "parle_g": "Parle-G",
    "oil": "Cooking oil",
}

DEFAULT_UNIT = {
    "sugar": "kg",
    "rice": "kg",
    "wheat_flour": "kg",
    "toor_dal": "kg",
    "tea": "pack",
    "parle_g": "pack",
    "oil": "l",
}

PRICE_BOOK = {
    "sugar": 44.0,
    "rice": 62.0,
    "wheat_flour": 38.0,
    "toor_dal": 118.0,
    "tea": 96.0,
    "parle_g": 10.0,
    "oil": 140.0,
}

DATE_RE = re.compile(r"(?P<date>\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})")
QTY_RE = re.compile(r"\b(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>kg|kgs|g|gm|l|ltr|pack|packs|pcs|pc)\b", re.I)
AMOUNT_RE = re.compile(r"(?:rs\.?|inr|₹)?\s*(?P<amount>\d+(?:\.\d+)?)", re.I)
EXPLICIT_AMOUNT_RE = re.compile(r"(?:rs\.?|inr|₹)\s*(?P<amount>\d+(?:\.\d+)?)", re.I)


def clean_text(text: str) -> str:
    """Normalize informal shop text without destroying transliterated words."""

    text = text.lower().strip()
    text = re.sub(r"[^\w\s:/.-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def canonicalize_sku(text: str) -> str:
    cleaned = clean_text(text)
    tokens = set(cleaned.replace("-", " ").split())
    for sku, aliases in SKU_ALIASES.items():
        if tokens.intersection(aliases):
            return sku
    for sku, aliases in SKU_ALIASES.items():
        if any(alias in cleaned for alias in aliases):
            return sku
    return cleaned.replace(" ", "_") or "unknown_item"


def display_name(sku: str) -> str:
    return DISPLAY_NAMES.get(sku, sku.replace("_", " ").title())


def normalize_unit(unit: str | None, sku: str) -> str:
    if not unit:
        return DEFAULT_UNIT.get(sku, "unit")
    unit = unit.lower()
    if unit in {"kgs", "kg"}:
        return "kg"
    if unit in {"g", "gm"}:
        return "g"
    if unit in {"ltr", "l"}:
        return "l"
    if unit in {"pcs", "pc"}:
        return "pcs"
    if unit == "packs":
        return "pack"
    return unit


def normalize_date(value: str | None) -> str:
    if not value:
        return datetime.today().strftime("%Y-%m-%d")
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.today().strftime("%Y-%m-%d")


def extract_quantity(text: str, sku: str) -> tuple[float, str]:
    match = QTY_RE.search(clean_text(text))
    if not match:
        return 1.0, DEFAULT_UNIT.get(sku, "unit")
    qty = float(match.group("qty"))
    unit = normalize_unit(match.group("unit"), sku)
    return qty, unit


def estimate_amount(sku: str, quantity: float) -> float:
    return round(PRICE_BOOK.get(sku, 50.0) * quantity, 2)


def parse_ledger_line(line: str) -> LedgerRecord:
    """Parse one OCR line into a structured ledger record.

    The trained OCR model should produce the text. This parser is the
    deterministic bridge from text to business fields.
    """

    cleaned = clean_text(line)
    date_match = DATE_RE.search(cleaned)
    date = normalize_date(date_match.group("date") if date_match else None)
    sku = canonicalize_sku(cleaned)
    quantity, unit = extract_quantity(cleaned, sku)

    amount_matches = list(AMOUNT_RE.finditer(cleaned))
    amount = estimate_amount(sku, quantity)
    if amount_matches:
        amount = float(amount_matches[-1].group("amount"))

    customer = "walk-in"
    if ":" in cleaned:
        left = cleaned.split(":", 1)[0]
        if date_match:
            left = left.replace(date_match.group("date"), "")
        parts = [part for part in left.split() if part]
        customer = parts[-1] if parts else customer
    elif "customer" in cleaned:
        customer = cleaned.split("customer", 1)[-1].split()[0]

    return LedgerRecord(
        date=date,
        item=sku,
        quantity=quantity,
        unit=unit,
        amount=amount,
        customer=customer,
    )


def parse_whatsapp_order(text: str) -> OrderIntent:
    cleaned = clean_text(text)
    customer = "whatsapp-customer"
    body = cleaned
    if ":" in cleaned:
        customer, body = cleaned.split(":", 1)
        customer = customer.strip() or "whatsapp-customer"

    sku = canonicalize_sku(body)
    quantity, unit = extract_quantity(body, sku)
    amount_match = EXPLICIT_AMOUNT_RE.search(body)
    return OrderIntent(
        customer=customer,
        item=sku,
        quantity=quantity,
        unit=unit,
        raw_text=text,
        amount=float(amount_match.group("amount")) if amount_match else None,
    )
