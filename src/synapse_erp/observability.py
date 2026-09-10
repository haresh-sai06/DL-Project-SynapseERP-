"""Small, dependency-free runtime observability for the local Synapse ERP API."""

from __future__ import annotations

import json
import math
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from synapse_erp.config import OUTPUT_DIR


class ObservabilityStore:
    """Thread-safe event journal with lightweight request benchmarks."""

    def __init__(self, max_events: int = 500, output_root: Path | None = None) -> None:
        self.started_at = time.time()
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._lock = threading.Lock()
        self._log_dir = (output_root or OUTPUT_DIR) / "logs"

    def record(
        self,
        category: str,
        message: str,
        *,
        level: str = "info",
        trace_id: str | None = None,
        duration_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": uuid4().hex,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": level,
            "category": category,
            "message": message,
            "trace_id": trace_id,
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
            "metadata": metadata or {},
        }
        with self._lock:
            self._events.append(event)
        self._persist(event)
        return event

    def recent(self, *, limit: int = 100, trace_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self._events)
        if trace_id:
            rows = [row for row in rows if row.get("trace_id") == trace_id]
        return rows[-max(1, min(limit, 500)) :]

    def snapshot(self, limit: int = 80) -> dict[str, Any]:
        events = self.recent(limit=500)
        requests = [event for event in events if event["category"] == "http.request"]
        durations = sorted(
            float(event["duration_ms"])
            for event in requests
            if event.get("duration_ms") is not None
        )
        errors = sum(1 for event in requests if int(event["metadata"].get("status", 0)) >= 500)
        conversions = [event for event in events if event["category"] == "conversion.completed"]
        return {
            "status": "operational",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "metrics": {
                "requests": len(requests),
                "errors": errors,
                "error_rate": round(errors / len(requests), 4) if requests else 0.0,
                "average_latency_ms": round(sum(durations) / len(durations), 2) if durations else 0.0,
                "p95_latency_ms": self._percentile(durations, 0.95),
                "completed_conversions": len(conversions),
            },
            "events": events[-max(1, min(limit, 200)) :],
        }

    def _persist(self, event: dict[str, Any]) -> None:
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            day = event["timestamp"][:10]
            with (self._log_dir / f"runtime-{day}.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            return

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        index = max(0, math.ceil(len(values) * percentile) - 1)
        return round(values[index], 2)


observability = ObservabilityStore()
