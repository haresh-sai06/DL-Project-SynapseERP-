"""FastAPI app for the Synapse ERP platform."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from synapse_erp.config import MODEL_DIR, OUTPUT_DIR, PROJECT_ROOT
from synapse_erp.erp import render_erp_html
from synapse_erp.live_data import fetch_historical_fx, get_market_snapshot
from synapse_erp.pipeline import SynapseERPPipeline
from synapse_erp.platform import StartupConversionService, safe_upload_name
from synapse_erp.web import PLATFORM_HTML
from synapse_erp.workspace import DemoAuthService, LoginRequest, WorkspaceStore


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
auth_service = DemoAuthService()
workspace_store = WorkspaceStore()


@app.get("/", response_class=HTMLResponse)
def platform_home() -> str:
    return PLATFORM_HTML


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/services")
def services() -> dict[str, list[dict]]:
    return {"services": conversion_service.services()}


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
def login(payload: LoginRequest) -> dict[str, Any]:
    try:
        return auth_service.login(payload)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.post("/api/convert")
async def convert(
    ledger_images: list[UploadFile] | None = File(default=None),
    product_images: list[UploadFile] | None = File(default=None),
    ledger_text: str = Form(default=""),
    chat_text: str = Form(default=""),
    product_hints: str = Form(default=""),
) -> dict:
    conversion_id = conversion_service._new_conversion_id()
    upload_dir = OUTPUT_DIR / "uploads" / conversion_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    ledger_paths = await _save_uploads(ledger_images or [], upload_dir, "ledger_note")
    product_paths = await _save_uploads(product_images or [], upload_dir, "product_photo")
    result = conversion_service.run_conversion(
        conversion_id=conversion_id,
        ledger_image_paths=ledger_paths,
        product_image_paths=product_paths,
        ledger_text=ledger_text,
        chat_text=chat_text,
        product_hints=product_hints,
    )
    workspace_store.get_workspace(result.conversion_id)
    return result.to_dict()


@app.post("/api/demo-conversion")
async def demo_conversion() -> dict:
    conversion_id = conversion_service._new_conversion_id()
    upload_dir = OUTPUT_DIR / "uploads" / conversion_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    ledger_paths, product_paths = _copy_demo_assets(upload_dir)
    ledger_text = """2026-06-01 ramesh: chini 2 kg Rs 88
2026-06-01 anita: rice 5 kg Rs 310
2026-06-02 salim: parle-g 10 pack Rs 100
2026-06-03 kavya: atta 3 kg Rs 114"""
    chat_text = """kavya: bhaiya 2kg atta bhej do
mahesh: need 1 l oil today
anita: kal ke liye 3 kg dal"""
    result = conversion_service.run_conversion(
        conversion_id=conversion_id,
        ledger_image_paths=ledger_paths,
        product_image_paths=product_paths,
        ledger_text=ledger_text,
        chat_text=chat_text,
        product_hints="sugar\nrice\nparle-g",
    )
    workspace_store.get_workspace(result.conversion_id)
    return result.to_dict()


@app.get("/api/workspaces/{conversion_id}")
def get_workspace(conversion_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_auth(authorization)
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
    _require_auth(authorization)
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
    _require_auth(authorization)
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
    _require_auth(authorization)
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
    _require_auth(authorization)
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
    return pipeline.ingest().to_dict()


@app.get("/erp", response_class=HTMLResponse)
def erp() -> str:
    snapshot = pipeline.ingest()
    html_path = render_erp_html(snapshot)
    return html_path.read_text(encoding="utf-8")


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


def _copy_demo_assets(upload_dir: Path) -> tuple[list[Path], list[Path]]:
    demo_dir = PROJECT_ROOT / "assets" / "demo"
    ledger_paths: list[Path] = []
    product_paths: list[Path] = []
    for source in sorted(demo_dir.glob("ledger_*.png")):
        target = _unique_path(upload_dir / source.name)
        shutil.copyfile(source, target)
        ledger_paths.append(target)
    for source in sorted(demo_dir.glob("product_*.png")):
        target = _unique_path(upload_dir / source.name)
        shutil.copyfile(source, target)
        product_paths.append(target)
    return ledger_paths, product_paths


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not allocate upload path for {path.name}")


def _require_auth(authorization: str | None) -> dict[str, Any]:
    try:
        return auth_service.verify(authorization)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
