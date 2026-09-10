"""FastAPI app for the Synapse ERP platform."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Body, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from synapse_erp.config import MODEL_DIR, OUTPUT_DIR, PROJECT_ROOT
from synapse_erp.erp import render_erp_html
from synapse_erp.live_data import fetch_historical_fx, get_market_snapshot
from synapse_erp.observability import observability
from synapse_erp.pipeline import SynapseERPPipeline
from synapse_erp.platform import StartupConversionService, safe_upload_name
from synapse_erp.web import PLATFORM_HTML
from synapse_erp.workspace import WorkspaceStore


class IngestRequest(BaseModel):
    ledger_lines: list[str] | None = None
    chat_lines: list[str] | None = None


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(PROJECT_ROOT / "docs").mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Synapse ERP", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:3001",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/generated", StaticFiles(directory=OUTPUT_DIR), name="generated")
app.mount("/project-assets", StaticFiles(directory=PROJECT_ROOT / "docs"), name="project-assets")

pipeline = SynapseERPPipeline()
conversion_service = StartupConversionService()
workspace_store = WorkspaceStore()
_CONVERSION_JOBS: dict[str, dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()


@app.middleware("http")
async def observe_request(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or conversion_service._new_conversion_id()
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["x-request-id"] = request_id
        return response
    finally:
        if request.url.path != "/api/observability":
            duration_ms = (time.perf_counter() - started) * 1000
            observability.record(
                "http.request",
                f"{request.method} {request.url.path}",
                level="error" if status >= 500 else "info",
                trace_id=request_id,
                duration_ms=duration_ms,
                metadata={"method": request.method, "path": request.url.path, "status": status},
            )


@app.get("/", response_class=HTMLResponse)
def platform_home() -> str:
    return PLATFORM_HTML


@app.get("/health")
def health() -> dict[str, object]:
    snapshot = observability.snapshot(limit=1)
    return {
        "status": "ok",
        "uptime_seconds": snapshot["uptime_seconds"],
        "requests_observed": snapshot["metrics"]["requests"],
    }


@app.get("/api/observability")
def runtime_observability(limit: int = 80) -> dict[str, object]:
    """Measured request benchmarks and the recent durable runtime event stream."""
    snapshot = observability.snapshot(limit=limit)
    with _JOBS_LOCK:
        jobs = list(_CONVERSION_JOBS.values())
    snapshot["jobs"] = {
        "queued": sum(job["status"] == "queued" for job in jobs),
        "running": sum(job["status"] == "running" for job in jobs),
        "completed": sum(job["status"] == "completed" for job in jobs),
        "failed": sum(job["status"] == "failed" for job in jobs),
    }
    snapshot["sources"] = [
        {"name": "Frankfurter / ECB", "kind": "live API", "refresh_seconds": 600},
        {"name": "CoinGecko", "kind": "live API", "refresh_seconds": 120},
        {"name": "Local conversion inputs", "kind": "submitted records", "refresh_seconds": 0},
        {"name": "Model metrics", "kind": "persisted benchmark artifacts", "refresh_seconds": 0},
    ]
    return snapshot


@app.get("/api/services")
def services() -> dict[str, list[dict]]:
    return {"services": conversion_service.services()}


@app.post("/api/conversions", status_code=202)
async def start_conversion(
    background_tasks: BackgroundTasks,
    ledger_images: list[UploadFile] | None = File(default=None),
    product_images: list[UploadFile] | None = File(default=None),
    ledger_text: str = Form(default=""),
    chat_text: str = Form(default=""),
    product_hints: str = Form(default=""),
) -> dict[str, object]:
    """Queue a conversion and return immediately so clients can watch real progress."""
    if not ledger_text.strip() and not chat_text.strip() and not (ledger_images or []):
        raise HTTPException(status_code=422, detail="Submit ledger text, a ledger image, or chat order text.")
    conversion_id = conversion_service._new_conversion_id()
    upload_dir = OUTPUT_DIR / "uploads" / conversion_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    ledger_paths = await _save_uploads(ledger_images or [], upload_dir, "ledger_note")
    product_paths = await _save_uploads(product_images or [], upload_dir, "product_photo")
    job = {
        "job_id": conversion_id,
        "conversion_id": conversion_id,
        "status": "queued",
        "progress": 0,
        "created_at": _utc_now(),
        "started_at": None,
        "completed_at": None,
        "duration_ms": None,
        "events": [],
        "nodes": {},
        "result": None,
        "error": None,
    }
    with _JOBS_LOCK:
        _CONVERSION_JOBS[conversion_id] = job
    queued = observability.record(
        "conversion.queued",
        "Conversion accepted and queued.",
        trace_id=conversion_id,
        metadata={"ledger_images": len(ledger_paths), "product_images": len(product_paths)},
    )
    job["events"].append(queued)
    background_tasks.add_task(
        _run_conversion_job,
        conversion_id,
        ledger_paths,
        product_paths,
        ledger_text,
        chat_text,
        product_hints,
    )
    return _job_view(job)


@app.get("/api/conversions/{job_id}")
def get_conversion_job(job_id: str) -> dict[str, object]:
    with _JOBS_LOCK:
        job = _CONVERSION_JOBS.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Conversion job {job_id} was not found.")
        return _job_view(job)


@app.get("/api/live")
def live_market() -> dict[str, object]:
    """Live FX + crypto market snapshot (real data, cached with graceful fallback)."""
    return get_market_snapshot()


@app.get("/api/live/history")
def live_history(base: str = "USD", symbol: str = "INR", years: int = 5) -> dict[str, object]:
    """Real historical daily series for a currency pair (Frankfurter / ECB)."""
    from datetime import date, timedelta

    end = date.today()
    start = end - timedelta(days=365 * max(1, min(years, 20)))
    series = fetch_historical_fx(start.isoformat(), end.isoformat(), base=base, symbol=symbol)
    return {
        "base": base,
        "symbol": symbol,
        "points": len(series),
        "series": series,
        "source": "Frankfurter / ECB",
    }


@app.get("/api/models")
def list_models() -> dict[str, object]:
    """List trained model artifacts and their last recorded metrics."""
    metrics_dir = OUTPUT_DIR / "metrics"
    models: list[dict[str, object]] = []
    if metrics_dir.exists():
        for path in sorted(metrics_dir.glob("*_metrics.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            name = path.name.replace("_metrics.json", "")
            figure = f"/generated/figures/{name}_loss.png"
            models.append(
                {
                    "name": name,
                    "metrics": data,
                    "loss_curve": figure,
                    "trained": True,
                }
            )
    return {"models": models, "model_dir": str(MODEL_DIR)}


@app.post("/api/train/forecaster")
def train_forecaster(payload: dict | None = Body(default=None)) -> dict[str, object]:
    """Trigger REAL DL training of the LSTM demand forecaster on live FX data."""
    import argparse

    from train_forecaster import train as train_forecaster_fn

    payload = payload or {}
    args = argparse.Namespace(
        source=payload.get("source", "real"),
        sku=payload.get("sku", "sugar"),
        days=int(payload.get("days", 220)),
        base=payload.get("base", "USD"),
        symbol=payload.get("symbol", "INR"),
        years=int(payload.get("years", 5)),
        window=int(payload.get("window", 14)),
        epochs=int(payload.get("epochs", 6)),
        batch_size=int(payload.get("batch_size", 32)),
        hidden_size=int(payload.get("hidden_size", 48)),
        lr=float(payload.get("lr", 1e-3)),
    )
    metrics = train_forecaster_fn(args)
    return {
        "ok": True,
        "model": "forecaster",
        "metrics": metrics,
        "loss_curve": "/generated/figures/forecast_loss.png",
    }


@app.post("/api/train/vision")
def train_vision(payload: dict | None = Body(default=None)) -> dict[str, object]:
    """Trigger REAL DL training of the CNN vision encoder on the real MNIST dataset."""
    import argparse

    from train_vision import train as train_vision_fn

    payload = payload or {}
    args = argparse.Namespace(
        epochs=int(payload.get("epochs", 3)),
        batch_size=int(payload.get("batch_size", 64)),
        lr=float(payload.get("lr", 1e-3)),
    )
    metrics = train_vision_fn(args)
    return {
        "ok": True,
        "model": "vision_cnn",
        "metrics": metrics,
        "loss_curve": "/generated/figures/vision_cnn_loss.png",
    }


# ---------------------------------------------------------------------------
# Model inference serving — loads trained weights and runs real predictions
# ---------------------------------------------------------------------------
_VISION_MODEL: tuple | None = None          # (model, test_set, transform)


@app.get("/api/inference/vision/random")
def vision_inference_random() -> dict[str, object]:
    """Pick a random real MNIST test image, predict it, return the result."""
    import torch
    from torchvision import transforms
    from torchvision.datasets import MNIST
    from train_vision import build_model

    global _VISION_MODEL
    ckp = MODEL_DIR / "best_vision_cnn.pt"
    if not ckp.exists():
        return {"ok": False, "error": "No trained vision model. Run /api/train/vision first."}

    if _VISION_MODEL is None:
        model = build_model()
        state = torch.load(ckp, map_location="cpu", weights_only=False)
        model.load_state_dict(state["model_state"])
        model.eval()
        transform = transforms.Compose(
            [transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))]
        )
        test_set = MNIST(root=str(OUTPUT_DIR / "datasets"), train=False, transform=transform)
        _VISION_MODEL = (model, test_set, transform)

    model, test_set, _ = _VISION_MODEL
    idx = int(torch.randint(0, len(test_set), (1,)).item())
    img, label = test_set[idx]
    with torch.no_grad():
        logits = model(img.unsqueeze(0))
        pred = int(logits.argmax(dim=1).item())
        probs = torch.softmax(logits, dim=1).squeeze(0).tolist()

    return {
        "ok": True,
        "sample_index": idx,
        "true_label": int(label),
        "predicted_label": pred,
        "correct": pred == int(label),
        "confidence": probs[pred],
        "all_probs": [round(p, 4) for p in probs],
    }


@app.post("/api/inference/vision")
def vision_inference_post(payload: dict = Body(...)) -> dict[str, object]:
    """Classify a 28×28 grayscale image sent as a flat 784-float array."""
    import torch
    from torchvision import transforms
    from train_vision import build_model

    import numpy as np

    global _VISION_MODEL
    ckp = MODEL_DIR / "best_vision_cnn.pt"
    if not ckp.exists():
        return {"ok": False, "error": "No trained vision model. Run /api/train/vision first."}

    if _VISION_MODEL is None:
        model = build_model()
        state = torch.load(ckp, map_location="cpu", weights_only=False)
        model.load_state_dict(state["model_state"])
        model.eval()
        transform = transforms.Compose(
            [transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))]
        )
        test_set = MNIST(root=str(OUTPUT_DIR / "datasets"), train=False, transform=transform)
        _VISION_MODEL = (model, test_set, transform)

    pixels = payload.get("pixels")
    if not pixels or len(pixels) != 784:
        return {"ok": False, "error": "Provide 784 float values (28×28 grayscale)."}

    model, _, transform = _VISION_MODEL
    arr = np.array(pixels, dtype=np.float32).reshape(28, 28)
    import torchvision.transforms.functional as F

    tensor = F.to_tensor(arr).unsqueeze(0)  # 1,1,28,28
    tensor = F.normalize(tensor, (0.1307,), (0.3081,))
    with torch.no_grad():
        logits = model(tensor)
        pred = int(logits.argmax(dim=1).item())
        probs = torch.softmax(logits, dim=1).squeeze(0).tolist()

    return {
        "ok": True,
        "predicted_label": pred,
        "confidence": probs[pred],
        "all_probs": [round(p, 4) for p in probs],
    }


@app.post("/api/inference/forecast")
def forecast_inference(payload: dict = Body(...)) -> dict[str, object]:
    """Predict the next value given recent observations."""
    import torch
    from synapse_erp.models.forecasting_architectures import LSTMDemandForecaster

    ckp = MODEL_DIR / "best_forecaster.pt"
    if not ckp.exists():
        return {"ok": False, "error": "No trained forecaster. Run /api/train/forecaster first."}

    values = payload.get("values")
    window = int(payload.get("window", 14))
    if not values or len(values) < window:
        return {"ok": False, "error": f"Provide at least {window} recent values."}

    model = LSTMDemandForecaster(hidden_size=48)
    state = torch.load(ckp, map_location="cpu", weights_only=False)
    model_state = state["model_state"] if "model_state" in state else state
    model.load_state_dict(model_state)
    model.eval()

    recent = torch.tensor(values[-window:], dtype=torch.float32).unsqueeze(0).unsqueeze(-1)
    with torch.no_grad():
        pred = float(model(recent).squeeze().item())

    return {
        "ok": True,
        "predicted_next": round(pred, 4),
        "based_on": len(values),
        "window": window,
    }


# ---------------------------------------------------------------------------
# Pre-trained model inference (HuggingFace transformers)
# Lazy-loaded so the API boots fast; first request downloads the model.
# ---------------------------------------------------------------------------
_PRETRAINED: dict[str, object] = {}


PRETRAINED_MODELS = {
    "ocr": {
        "id": "microsoft/trocr-base-handwritten",
        "task": "image-to-text",
        "description": "TrOCR — Microsoft's pre-trained transformer OCR for handwritten English text",
        "pipeline": "image-to-text",
        "loaded": False,
    },
    "ner": {
        "id": "dslim/bert-base-NER",
        "task": "token-classification",
        "description": "BERT-based multilingual NER — extracts person, product, quantity entities",
        "pipeline": "token-classification",
        "loaded": False,
    },
}


@app.get("/api/inference/pretrained-models")
def list_pretrained() -> dict[str, object]:
    """List all available pre-trained models and their load status."""
    return {
        "models": [
            {**info, "loaded": _PRETRAINED.get(key) is not None}
            for key, info in PRETRAINED_MODELS.items()
        ]
    }


@app.post("/api/inference/ocr")
def ocr_inference(payload: dict = Body(...)) -> dict[str, object]:
    """Recognize handwritten text using pre-trained TrOCR.

    Accept base64-encoded image (image/png) under the key 'image' (required).
    Returns the recognized text string.
    """
    import base64
    import io
    from PIL import Image

    key = "ocr"
    if key not in _PRETRAINED:
        try:
            from transformers import pipeline as hf_pipeline
            _PRETRAINED[key] = hf_pipeline(
                PRETRAINED_MODELS[key]["pipeline"],
                model=PRETRAINED_MODELS[key]["id"],
            )
        except Exception as exc:
            return {"ok": False, "error": f"Failed to load TrOCR model: {exc}"}

    image_b64 = payload.get("image")
    if not image_b64:
        return {"ok": False, "error": "Provide a base64-encoded image under the 'image' key."}

    try:
        image_bytes = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        pipe = _PRETRAINED[key]
        result = pipe(image)
        text = result[0]["generated_text"] if result else ""
        return {"ok": True, "text": text, "model": PRETRAINED_MODELS[key]["id"]}
    except Exception as exc:
        return {"ok": False, "error": f"OCR inference failed: {exc}"}


@app.post("/api/inference/ner")
def ner_inference(payload: dict = Body(...)) -> dict[str, object]:
    """Extract named entities from text using pre-trained BERT.

    Accepts a 'text' string. Returns list of entity dicts with
    word, entity_type, score, start, end.
    """
    key = "ner"
    if key not in _PRETRAINED:
        try:
            from transformers import pipeline as hf_pipeline
            _PRETRAINED[key] = hf_pipeline(
                PRETRAINED_MODELS[key]["pipeline"],
                model=PRETRAINED_MODELS[key]["id"],
                aggregation_strategy="simple",
            )
        except Exception as exc:
            return {"ok": False, "error": f"Failed to load NER model: {exc}"}

    text = payload.get("text", "")
    if not text.strip():
        return {"ok": False, "error": "Provide a non-empty 'text' string."}

    try:
        pipe = _PRETRAINED[key]
        entities = pipe(text)
        return {
            "ok": True,
            "text": text,
            "entities": [
                {
                    "word": e["word"],
                    "type": e["entity_group"],
                    "score": round(e["score"], 4),
                    "start": e["start"],
                    "end": e["end"],
                }
                for e in entities
            ],
            "model": PRETRAINED_MODELS[key]["id"],
        }
    except Exception as exc:
        return {"ok": False, "error": f"NER inference failed: {exc}"}


@app.post("/api/convert")
async def convert(
    ledger_images: list[UploadFile] | None = File(default=None),
    product_images: list[UploadFile] | None = File(default=None),
    ledger_text: str = Form(default=""),
    chat_text: str = Form(default=""),
    product_hints: str = Form(default=""),
) -> dict:
    if not ledger_text.strip() and not chat_text.strip() and not (ledger_images or []):
        raise HTTPException(status_code=422, detail="Submit ledger text, a ledger image, or chat order text.")
    conversion_id = conversion_service._new_conversion_id()
    upload_dir = OUTPUT_DIR / "uploads" / conversion_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    ledger_paths = await _save_uploads(ledger_images or [], upload_dir, "ledger_note")
    product_paths = await _save_uploads(product_images or [], upload_dir, "product_photo")
    events: list[dict[str, Any]] = []
    result = conversion_service.run_conversion(
        conversion_id=conversion_id,
        ledger_image_paths=ledger_paths,
        product_image_paths=product_paths,
        ledger_text=ledger_text,
        chat_text=chat_text,
        product_hints=product_hints,
        event_handler=lambda event: events.append(_record_node_event(conversion_id, event)),
    )
    workspace_store.get_workspace(result.conversion_id)
    payload = result.to_dict()
    payload["workspace_token"] = workspace_store.create_access_token(result.conversion_id)
    payload["runtime"] = {"events": events, "duration_ms": round(sum(node.latency_ms for node in result.nodes), 2)}
    return payload


@app.post("/api/demo-conversion")
async def demo_conversion() -> dict:
    raise HTTPException(
        status_code=410,
        detail="The mock conversion endpoint was retired. Submit real records to /api/conversions.",
    )


@app.get("/api/workspaces/{conversion_id}")
def get_workspace(conversion_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_auth(conversion_id, authorization)
    try:
        return workspace_store.get_workspace(conversion_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/workspaces/{conversion_id}/{resource}")
def list_workspace_resource(
    conversion_id: str,
    resource: str,
    authorization: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    _require_auth(conversion_id, authorization)
    try:
        return workspace_store.list_resource(conversion_id, resource)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/workspaces/{conversion_id}/{resource}")
def add_workspace_item(
    conversion_id: str,
    resource: str,
    item: dict[str, Any] = Body(...),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(conversion_id, authorization)
    try:
        return workspace_store.add_item(conversion_id, resource, item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/api/workspaces/{conversion_id}/{resource}/{item_id}")
def update_workspace_item(
    conversion_id: str,
    resource: str,
    item_id: str,
    patch: dict[str, Any] = Body(...),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(conversion_id, authorization)
    try:
        return workspace_store.update_item(conversion_id, resource, item_id, patch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/workspaces/{conversion_id}/{resource}/{item_id}")
def delete_workspace_item(
    conversion_id: str,
    resource: str,
    item_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(conversion_id, authorization)
    try:
        return workspace_store.delete_item(conversion_id, resource, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/ingest")
def ingest(payload: IngestRequest) -> dict:
    snapshot = pipeline.ingest(payload.ledger_lines, payload.chat_lines)
    return snapshot.to_dict()


@app.get("/demo")
def demo() -> dict:
    raise HTTPException(status_code=410, detail="The synthetic demo was retired. Submit real records to /ingest.")


@app.get("/erp", response_class=HTMLResponse)
def erp() -> str:
    raise HTTPException(status_code=410, detail="Generate an ERP from submitted records through /api/conversions.")


async def _save_uploads(files: list[UploadFile], upload_dir: Path, prefix: str) -> list[Path]:
    saved: list[Path] = []
    for index, upload in enumerate(files, start=1):
        content = await upload.read()
        if not content:
            continue
        filename = safe_upload_name(upload.filename or "", f"{prefix}_{index}")
        path = _unique_path(upload_dir / filename)
        path.write_bytes(content)
        saved.append(path)
    return saved


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not allocate upload path for {path.name}")


def _require_auth(conversion_id: str, authorization: str | None) -> None:
    try:
        workspace_store.verify_access(conversion_id, authorization)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _run_conversion_job(
    conversion_id: str,
    ledger_paths: list[Path],
    product_paths: list[Path],
    ledger_text: str,
    chat_text: str,
    product_hints: str,
) -> None:
    started = time.perf_counter()
    with _JOBS_LOCK:
        job = _CONVERSION_JOBS[conversion_id]
        job["status"] = "running"
        job["started_at"] = _utc_now()
    _append_job_event(
        conversion_id,
        observability.record("conversion.started", "Conversion worker started.", trace_id=conversion_id),
    )
    try:
        result = conversion_service.run_conversion(
            conversion_id=conversion_id,
            ledger_image_paths=ledger_paths,
            product_image_paths=product_paths,
            ledger_text=ledger_text,
            chat_text=chat_text,
            product_hints=product_hints,
            event_handler=lambda event: _handle_job_node_event(conversion_id, event),
        )
        workspace_store.get_workspace(result.conversion_id)
        token = workspace_store.create_access_token(result.conversion_id)
        duration_ms = (time.perf_counter() - started) * 1000
        completed = observability.record(
            "conversion.completed",
            "Conversion completed and workspace access initialized.",
            trace_id=conversion_id,
            duration_ms=duration_ms,
            metadata={"outputs": len(result.outputs), "nodes": len(result.nodes)},
        )
        _append_job_event(conversion_id, completed)
        with _JOBS_LOCK:
            job = _CONVERSION_JOBS[conversion_id]
            payload = result.to_dict()
            payload["workspace_token"] = token
            payload["runtime"] = {
                "duration_ms": round(duration_ms, 2),
                "events": list(job["events"]),
            }
            job.update(
                {
                    "status": "completed",
                    "progress": 100,
                    "completed_at": _utc_now(),
                    "duration_ms": round(duration_ms, 2),
                    "result": payload,
                }
            )
    except Exception as exc:
        duration_ms = (time.perf_counter() - started) * 1000
        failed = observability.record(
            "conversion.failed",
            str(exc),
            level="error",
            trace_id=conversion_id,
            duration_ms=duration_ms,
        )
        _append_job_event(conversion_id, failed)
        with _JOBS_LOCK:
            _CONVERSION_JOBS[conversion_id].update(
                {
                    "status": "failed",
                    "completed_at": _utc_now(),
                    "duration_ms": round(duration_ms, 2),
                    "error": str(exc),
                }
            )


def _handle_job_node_event(conversion_id: str, event: dict[str, Any]) -> None:
    recorded = _record_node_event(conversion_id, event)
    with _JOBS_LOCK:
        job = _CONVERSION_JOBS[conversion_id]
        job["events"].append(recorded)
        job["nodes"][event["node_id"]] = event
        completed = sum(node.get("status") == "completed" for node in job["nodes"].values())
        job["progress"] = round(completed / len(conversion_service.service_catalog) * 100)


def _record_node_event(conversion_id: str, event: dict[str, Any]) -> dict[str, Any]:
    return observability.record(
        "pipeline.node",
        event["message"],
        level="error" if event["status"] == "failed" else "info",
        trace_id=conversion_id,
        duration_ms=event.get("duration_ms"),
        metadata={"node_id": event["node_id"], "status": event["status"]},
    )


def _append_job_event(conversion_id: str, event: dict[str, Any]) -> None:
    with _JOBS_LOCK:
        _CONVERSION_JOBS[conversion_id]["events"].append(event)


def _job_view(job: dict[str, Any]) -> dict[str, object]:
    return {
        "job_id": job["job_id"],
        "conversion_id": job["conversion_id"],
        "status": job["status"],
        "progress": job["progress"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "completed_at": job["completed_at"],
        "duration_ms": job["duration_ms"],
        "events": list(job["events"]),
        "nodes": dict(job["nodes"]),
        "result": job["result"],
        "error": job["error"],
    }


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
