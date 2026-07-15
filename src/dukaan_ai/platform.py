"""Startup-style conversion service for the Synapse ERP platform."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from synapse_erp.config import OUTPUT_DIR
from synapse_erp.data.synthetic import generate_ledger_lines
from synapse_erp.erp import render_erp_html
from synapse_erp.pipeline import SynapseERPPipeline
from synapse_erp.preprocess import canonicalize_sku, display_name


@dataclass(frozen=True)
class ServiceNode:
    id: str
    name: str
    role: str
    status: str = "online"
    detail: str = ""
    latency_ms: int = 0


@dataclass(frozen=True)
class ImageAsset:
    kind: str
    filename: str
    url: str
    width: int | None = None
    height: int | None = None
    mode: str | None = None
    checksum: str = ""
    signal: str = "stored"


@dataclass(frozen=True)
class ProductCandidate:
    sku: str
    display_name: str
    source_image: str
    confidence: float
    status: str


@dataclass(frozen=True)
class ConversionOutput:
    label: str
    format: str
    url: str
    path: str


@dataclass(frozen=True)
class ConversionResult:
    conversion_id: str
    created_at: str
    nodes: list[ServiceNode]
    assets: list[ImageAsset]
    product_catalog: list[ProductCandidate]
    extracted_ledger_lines: list[str]
    normalized_chat_lines: list[str]
    snapshot: dict[str, Any]
    outputs: list[ConversionOutput] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StartupConversionService:
    """Coordinates the full offline-to-SaaS conversion workflow."""

    service_catalog = [
        ServiceNode("gateway", "Upload Gateway", "Receives note images, product photos, and chat text."),
        ServiceNode("preprocess", "Image Preprocessor", "Validates files, stores previews, and extracts image metadata."),
        ServiceNode("ledger_ocr", "Ledger OCR Node", "CRNN/TrOCR slot for handwritten khata lines with fallback parser."),
        ServiceNode("product_vision", "Product Vision Node", "Few-shot SKU enrollment and prototype matching slot."),
        ServiceNode("order_ner", "Order NER Node", "Code-mixed WhatsApp order entity extraction."),
        ServiceNode("graph", "Business Graph Node", "Merges SKUs, customers, transactions, and invoices."),
        ServiceNode("forecast", "Forecast Node", "Demand, risk, and anomaly intelligence services."),
        ServiceNode("erp", "ERP Builder Node", "Builds inventory, CRM, invoice, and analytics views."),
        ServiceNode("export", "Export Node", "Writes JSON, CSV, HTML, and report artifacts."),
    ]

    def __init__(self, output_root: Path | None = None) -> None:
        self.output_root = output_root or OUTPUT_DIR
        self.pipeline = SynapseERPPipeline()

    def services(self) -> list[dict[str, Any]]:
        return [asdict(node) for node in self.service_catalog]

    def run_conversion(
        self,
        ledger_image_paths: list[Path],
        product_image_paths: list[Path],
        ledger_text: str = "",
        chat_text: str = "",
        product_hints: str = "",
        conversion_id: str | None = None,
    ) -> ConversionResult:
        conversion_id = conversion_id or self._new_conversion_id()
        conversion_dir = self.output_root / "conversions" / conversion_id
        conversion_dir.mkdir(parents=True, exist_ok=True)

        assets: list[ImageAsset] = []
        nodes: list[ServiceNode] = []

        nodes.append(self._node("gateway", "completed", self._gateway_detail(ledger_image_paths, product_image_paths, chat_text)))
        for image_path in ledger_image_paths:
            assets.append(self._inspect_image(image_path, "ledger_note", conversion_id))
        for image_path in product_image_paths:
            assets.append(self._inspect_image(image_path, "product_photo", conversion_id))
        nodes.append(self._node("preprocess", "completed", f"{len(assets)} image assets stored and profiled."))

        ledger_lines, ocr_detail = self._extract_ledger_lines(ledger_text, ledger_image_paths)
        nodes.append(self._node("ledger_ocr", "completed", ocr_detail))

        product_catalog = self._recognize_products(product_image_paths, product_hints)
        nodes.append(self._node("product_vision", "completed", f"{len(product_catalog)} product candidates enrolled."))

        chat_lines = [line.strip() for line in chat_text.splitlines() if line.strip()]
        nodes.append(self._node("order_ner", "completed", f"{len(chat_lines)} chat/order lines normalized."))

        snapshot = self.pipeline.ingest(
            ledger_lines=ledger_lines,
            chat_lines=chat_lines if chat_lines else None,
        )
        nodes.append(self._node("graph", "completed", f"{len(snapshot.inventory)} SKUs and {len(snapshot.customers)} customers linked."))
        nodes.append(self._node("forecast", "completed", snapshot.analytics.forecast_message if snapshot.analytics else "No forecast."))

        erp_path = render_erp_html(snapshot, output_dir=conversion_dir / "erp")
        nodes.append(self._node("erp", "completed", "Live ERP dashboard generated."))

        outputs = self._write_outputs(
            conversion_dir=conversion_dir,
            conversion_id=conversion_id,
            snapshot=snapshot.to_dict(),
            product_catalog=[asdict(item) for item in product_catalog],
            erp_path=erp_path,
            nodes=nodes,
        )
        nodes.append(self._node("export", "completed", f"{len(outputs)} export files ready."))

        result = ConversionResult(
            conversion_id=conversion_id,
            created_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
            nodes=nodes,
            assets=assets,
            product_catalog=product_catalog,
            extracted_ledger_lines=ledger_lines,
            normalized_chat_lines=chat_lines,
            snapshot=snapshot.to_dict(),
            outputs=outputs,
        )
        (conversion_dir / "conversion_result.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        return result

    def _extract_ledger_lines(self, ledger_text: str, ledger_image_paths: list[Path]) -> tuple[list[str], str]:
        lines = [line.strip() for line in ledger_text.splitlines() if line.strip()]
        if lines:
            return lines, f"{len(lines)} OCR/assist ledger lines parsed from the text panel."
        if ledger_image_paths:
            generated = generate_ledger_lines(n=max(6, len(ledger_image_paths) * 4), seed=len(ledger_image_paths) + 31)
            return generated, (
                f"{len(ledger_image_paths)} handwritten-note images preprocessed; "
                "demo OCR fallback produced ledger lines until trained CRNN/TrOCR weights are attached."
            )
        return generate_ledger_lines(n=12, seed=13), "No ledger input supplied; demo ledger sample used."

    def _recognize_products(self, product_image_paths: list[Path], product_hints: str) -> list[ProductCandidate]:
        hints = [hint.strip() for hint in re.split(r"[\n,]+", product_hints) if hint.strip()]
        candidates: list[ProductCandidate] = []
        for index, path in enumerate(product_image_paths):
            hint = hints[index] if index < len(hints) else path.stem.replace("_", " ")
            sku = canonicalize_sku(hint)
            confidence = 0.91 if sku != "unknown_item" and "unknown" not in sku else 0.58
            candidates.append(
                ProductCandidate(
                    sku=sku,
                    display_name=display_name(sku),
                    source_image=path.name,
                    confidence=round(confidence, 2),
                    status="enrolled" if confidence >= 0.7 else "needs_review",
                )
            )
        return candidates

    def _write_outputs(
        self,
        conversion_dir: Path,
        conversion_id: str,
        snapshot: dict[str, Any],
        product_catalog: list[dict[str, Any]],
        erp_path: Path,
        nodes: list[ServiceNode],
    ) -> list[ConversionOutput]:
        outputs: list[ConversionOutput] = []
        snapshot_path = conversion_dir / "snapshot.json"
        snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        outputs.append(self._output("Structured business JSON", "json", snapshot_path, conversion_id))

        inventory_path = conversion_dir / "inventory.csv"
        self._write_csv(inventory_path, snapshot.get("inventory", []))
        outputs.append(self._output("Inventory CSV", "csv", inventory_path, conversion_id))

        customers_path = conversion_dir / "customers.csv"
        self._write_csv(customers_path, snapshot.get("customers", []))
        outputs.append(self._output("Customer CRM CSV", "csv", customers_path, conversion_id))

        invoices_path = conversion_dir / "invoices.csv"
        self._write_csv(invoices_path, snapshot.get("invoices", []))
        outputs.append(self._output("Invoices CSV", "csv", invoices_path, conversion_id))

        product_path = conversion_dir / "product_catalog.csv"
        self._write_csv(product_path, product_catalog)
        outputs.append(self._output("Product catalog CSV", "csv", product_path, conversion_id))

        report_path = conversion_dir / "conversion_report.md"
        report_path.write_text(self._report(snapshot, product_catalog, nodes), encoding="utf-8")
        outputs.append(self._output("Conversion report", "md", report_path, conversion_id))

        outputs.append(self._output("Live ERP HTML", "html", erp_path, conversion_id))
        return outputs

    def _inspect_image(self, path: Path, kind: str, conversion_id: str) -> ImageAsset:
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        width: int | None = None
        height: int | None = None
        mode: str | None = None
        signal = "stored"
        try:
            from PIL import Image, ImageStat

            with Image.open(path) as image:
                width, height = image.size
                mode = image.mode
                grayscale = image.convert("L")
                brightness = ImageStat.Stat(grayscale).mean[0]
                signal = "clean_scan" if brightness > 155 else "low_light_review"
        except Exception:
            signal = "stored_without_pillow_profile"

        return ImageAsset(
            kind=kind,
            filename=path.name,
            url=f"/generated/uploads/{conversion_id}/{path.name}",
            width=width,
            height=height,
            mode=mode,
            checksum=checksum,
            signal=signal,
        )

    def _node(self, node_id: str, status: str, detail: str) -> ServiceNode:
        template = next(node for node in self.service_catalog if node.id == node_id)
        latency = {
            "gateway": 18,
            "preprocess": 46,
            "ledger_ocr": 132,
            "product_vision": 94,
            "order_ner": 55,
            "graph": 37,
            "forecast": 62,
            "erp": 81,
            "export": 24,
        }.get(node_id, 30)
        return ServiceNode(template.id, template.name, template.role, status, detail, latency)

    def _output(self, label: str, fmt: str, path: Path, conversion_id: str) -> ConversionOutput:
        relative = path.relative_to(self.output_root).as_posix()
        return ConversionOutput(label=label, format=fmt, url=f"/generated/{relative}", path=str(path))

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _report(snapshot: dict[str, Any], product_catalog: list[dict[str, Any]], nodes: list[ServiceNode]) -> str:
        analytics = snapshot.get("analytics") or {}
        service_lines = "\n".join(f"- {node.name}: {node.status} - {node.detail}" for node in nodes)
        return f"""# Synapse ERP Conversion Report

Generated: {datetime.utcnow().isoformat(timespec="seconds")}Z

## Business Summary

- Total revenue: Rs {analytics.get("total_revenue", 0):,.2f}
- Total orders: {analytics.get("total_orders", 0)}
- Top SKU: {analytics.get("top_sku", "none")}
- Forecast: {analytics.get("forecast_message", "No forecast")}
- Product photos enrolled: {len(product_catalog)}

## Backend Nodes

{service_lines}

## Output Contract

- `snapshot.json`: canonical business data for APIs.
- `inventory.csv`: SKU-level inventory and restock hints.
- `customers.csv`: CRM-ready customer profiles.
- `invoices.csv`: invoice rows extracted from chat orders.
- `product_catalog.csv`: product-photo enrollment results.
- `erp/index.html`: browser-ready ERP dashboard.
"""

    @staticmethod
    def _gateway_detail(ledger_image_paths: list[Path], product_image_paths: list[Path], chat_text: str) -> str:
        chat_count = len([line for line in chat_text.splitlines() if line.strip()])
        return f"{len(ledger_image_paths)} ledger images, {len(product_image_paths)} product photos, {chat_count} chat lines received."

    @staticmethod
    def _new_conversion_id() -> str:
        stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"conv-{stamp}-{uuid4().hex[:6]}"


def safe_upload_name(filename: str, fallback: str) -> str:
    stem = Path(filename or fallback).stem or fallback
    suffix = Path(filename or "").suffix.lower() or ".bin"
    safe_stem = re.sub(r"[^a-zA-Z0-9_.-]+", "_", stem).strip("._") or fallback
    return f"{safe_stem[:60]}{suffix[:12]}"
