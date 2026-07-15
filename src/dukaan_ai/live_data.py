"""Real-time market data feeds for the Synapse ERP platform.

All data is fetched live from public, key-less APIs:

* Frankfurter (ECB reference rates) for fiat FX rates and historical series:
  https://frankfurter.dev
* CoinGecko for live cryptocurrency spot prices:
  https://www.coingecko.com/en/api

Results are cached in memory (with a TTL) and mirrored to a JSON file so the
UI keeps working across restarts. If the network is unavailable the last good
snapshot is served instead of fabricating numbers.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # requests is bundled with some deps; fall back to urllib otherwise.
    import requests
except Exception:  # pragma: no cover - requests is almost always present
    requests = None  # type: ignore

from synapse_erp.config import OUTPUT_DIR

CACHE_DIR = OUTPUT_DIR / "live_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

FX_BASE_URL = "https://api.frankfurter.dev/v1"
CRYPTO_URL = "https://api.coingecko.com/api/v3/simple/price"
COMMODITY_URL = "https://api.gold-api.com/price"

FX_TTL_SECONDS = 60 * 10          # ECB rates update once per business day
CRYPTO_TTL_SECONDS = 60 * 2       # crypto moves fast, refresh often
COMMODITY_TTL_SECONDS = 60 * 10
HISTORY_TTL_SECONDS = 60 * 30

_LOCK = threading.Lock()
_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}


@dataclass
class _Cached:
    value: Any
    fetched_at: float


def _now() -> float:
    return time.time()


def _read_file_cache(key: str) -> Optional[Any]:
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_file_cache(key: str, value: Any) -> None:
    path = CACHE_DIR / f"{key}.json"
    try:
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    except Exception:
        return


def _get_cached(key: str, ttl: int) -> Optional[Any]:
    with _LOCK:
        item = _MEMORY_CACHE.get(key)
        if item is not None and (_now() - item.fetched_at) < ttl:
            return item.value
    file_value = _read_file_cache(key)
    if file_value is not None:
        with _LOCK:
            _MEMORY_CACHE[key] = _Cached(file_value, _now())
        return file_value
    return None


def _set_cached(key: str, value: Any) -> None:
    with _LOCK:
        _MEMORY_CACHE[key] = _Cached(value, _now())
    _write_file_cache(key, value)


def _http_get_json(url: str, params: Optional[Dict[str, str]] = None, timeout: int = 12) -> Dict[str, Any]:
    if requests is not None:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    import urllib.request
    import urllib.parse

    full = url
    if params:
        full = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(full, timeout=timeout) as handle:  # noqa: S310
        return json.loads(handle.read().decode("utf-8"))


# --------------------------------------------------------------------------- #
# FX rates
# --------------------------------------------------------------------------- #
def fetch_fx_rates(base: str = "USD") -> Dict[str, Any]:
    """Live fiat FX rates from the Frankfurter / ECB reference set."""
    key = f"fx_{base.upper()}"
    cached = _get_cached(key, FX_TTL_SECONDS)
    if cached is not None:
        return cached

    payload = _http_get_json(f"{FX_BASE_URL}/latest", params={"base": base.upper()})
    result = {
        "base": payload.get("base", base.upper()),
        "date": payload.get("date"),
        "rates": payload.get("rates", {}),
        "source": "Frankfurter / ECB",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "live": True,
    }
    _set_cached(key, result)
    return result


# --------------------------------------------------------------------------- #
# Crypto prices
# --------------------------------------------------------------------------- #
DEFAULT_COINS = [
    ("bitcoin", "btc"),
    ("ethereum", "eth"),
    ("tether", "usdt"),
    ("binancecoin", "bnb"),
    ("solana", "sol"),
    ("ripple", "xrp"),
]


def fetch_crypto_prices(ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Live crypto spot prices (USD) from CoinGecko."""
    ids = ids or [coin[0] for coin in DEFAULT_COINS]
    key = "crypto_" + "_".join(ids)
    cached = _get_cached(key, CRYPTO_TTL_SECONDS)
    if cached is not None:
        return cached

    payload = _http_get_json(
        CRYPTO_URL,
        params={"ids": ",".join(ids), "vs_currencies": "usd,inr", "include_24hr_change": "true"},
    )
    coins = []
    for coin_id, symbol in DEFAULT_COINS:
        row = payload.get(coin_id)
        if not row:
            continue
        coins.append(
            {
                "id": coin_id,
                "symbol": symbol,
                "usd": row.get("usd"),
                "inr": row.get("inr"),
                "change_24h": row.get("usd_24h_change"),
            }
        )
    result = {
        "coins": coins,
        "source": "CoinGecko",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "live": True,
    }
    _set_cached(key, result)
    return result


# --------------------------------------------------------------------------- #
# Precious metals (gold, silver) — free, no-key API
# --------------------------------------------------------------------------- #
PRECIOUS_METALS = [
    ("XAU", "Gold", "XAU"),
    ("XAG", "Silver", "XAG"),
]


def fetch_commodity_prices() -> Dict[str, Any]:
    """Live precious-metal spot prices (USD) from gold-api.com (free, no key)."""
    key = "commodities"
    cached = _get_cached(key, COMMODITY_TTL_SECONDS)
    if cached is not None:
        return cached

    items = []
    for sym, name, _ in PRECIOUS_METALS:
        try:
            payload = _http_get_json(f"{COMMODITY_URL}/{sym}", timeout=8)
            items.append(
                {
                    "symbol": sym,
                    "name": name,
                    "price_usd": payload.get("price"),
                    "updated_at": payload.get("updatedAt"),
                }
            )
        except Exception:
            continue

    result = {
        "commodities": items,
        "source": "gold-api.com",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "live": bool(items),
    }
    if items:
        _set_cached(key, result)
    return result


# ---------------------------------------------------------------------------
# Historical series (used for charts and real DL training)
# --------------------------------------------------------------------------- #
def fetch_historical_fx(start: str, end: str, base: str = "USD", symbol: str = "INR") -> List[Dict[str, Any]]:
    """Daily historical FX rates between `base` and `symbol` (real ECB data)."""
    key = f"hist_{base}_{symbol}_{start}_{end}"
    cached = _get_cached(key, HISTORY_TTL_SECONDS)
    if cached is not None:
        return cached

    payload = _http_get_json(
        f"{FX_BASE_URL}/{start}..{end}",
        params={"base": base.upper(), "symbols": symbol.upper()},
    )
    series: List[Dict[str, Any]] = []
    rates = payload.get("rates", {})
    for day, day_rates in rates.items():
        if symbol.upper() in day_rates:
            series.append({"date": day, "value": float(day_rates[symbol.upper()])})
    series.sort(key=lambda item: item["date"])
    _set_cached(key, series)
    return series


def default_history_symbols() -> List[Dict[str, str]]:
    """Currency pairs that matter for an import-cost-aware Indian shop."""
    today = date.today()
    start = (today - timedelta(days=365 * 3)).isoformat()
    end = today.isoformat()
    return [
        {"base": "USD", "symbol": "INR", "label": "USD → INR", "start": start, "end": end},
        {"base": "EUR", "symbol": "INR", "label": "EUR → INR", "start": start, "end": end},
        {"base": "AED", "symbol": "INR", "label": "AED → INR", "start": start, "end": end},
        {"base": "USD", "symbol": "CNY", "label": "USD → CNY", "start": start, "end": end},
    ]


# --------------------------------------------------------------------------- #
# Combined market snapshot
# --------------------------------------------------------------------------- #
def get_market_snapshot() -> Dict[str, Any]:
    """Build a combined live snapshot, degrading gracefully when offline."""
    offline = False
    try:
        fx = fetch_fx_rates("USD")
    except Exception:
        fx = _read_file_cache("fx_USD") or {
            "base": "USD",
            "date": None,
            "rates": {"INR": 83.0},
            "source": "offline-cache",
            "live": False,
        }
        offline = True

    try:
        crypto = fetch_crypto_prices()
    except Exception:
        crypto = _read_file_cache("crypto_" + "_".join(c[0] for c in DEFAULT_COINS)) or {
            "coins": [],
            "source": "offline-cache",
            "live": False,
        }
        offline = True

    try:
        commodities = fetch_commodity_prices()
    except Exception:
        commodities = _read_file_cache("commodities") or {"commodities": [], "source": "offline-cache", "live": False}
        offline = True

    return {
        "fx": fx,
        "crypto": crypto,
        "commodities": commodities,
        "live": not offline,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "note": "Live market data. Rates are for import-cost awareness, not financial advice."
        if not offline
        else "Network unavailable - showing last cached snapshot.",
    }


if __name__ == "__main__":
    import pprint

    pprint.pprint(get_market_snapshot())
    print("\n--- 30d USD/INR history (head) ---")
    hist = fetch_historical_fx("2023-01-01", "2023-01-31", "USD", "INR")
    pprint.pprint(hist[:5])
