"""Create docs/architecture.png without requiring an external diagram tool."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def main() -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as exc:
        raise ImportError("Pillow is required. Run `python -m pip install pillow`.") from exc

    out = PROJECT_ROOT / "docs" / "architecture.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1600, 920
    img = Image.new("RGB", (width, height), "#f7f7f2")
    draw = ImageDraw.Draw(img)
    font_title = ImageFont.truetype("arial.ttf", 44) if _has_arial() else ImageFont.load_default()
    font_box = ImageFont.truetype("arial.ttf", 26) if _has_arial() else ImageFont.load_default()
    font_small = ImageFont.truetype("arial.ttf", 21) if _has_arial() else ImageFont.load_default()

    draw.text((60, 38), "Synapse ERP: Offline Records to Forecasting ERP", fill="#1b1f23", font=font_title)
    draw.text((62, 94), "Trained perception models feed a business graph; intelligence models power ERP decisions.", fill="#52616b", font=font_small)

    boxes = {
        "ledger": (70, 190, 360, 300, "Ledger photo", "Handwritten khata"),
        "product": (70, 385, 360, 495, "Product photo", "Few-shot reference"),
        "chat": (70, 580, 360, 690, "WhatsApp orders", "Code-mixed text"),
        "ocr": (500, 175, 840, 315, "Ledger OCR", "CRNN + CTC / TrOCR"),
        "metric": (500, 370, 840, 510, "Product encoder", "Triplet/prototype loss"),
        "ner": (500, 565, 840, 705, "Order NER", "MuRIL / IndicBERT"),
        "graph": (970, 315, 1300, 485, "Business graph", "SKU, customer, invoice links"),
        "forecast": (970, 575, 1300, 725, "Intelligence", "LSTM forecast, risk, anomaly"),
        "erp": (1370, 350, 1540, 650, "ERP", "Inventory\nCRM\nInvoices\nAnalytics"),
    }
    colors = {
        "ledger": "#d9eadf",
        "product": "#e7edf7",
        "chat": "#fff0cf",
        "ocr": "#ffffff",
        "metric": "#ffffff",
        "ner": "#ffffff",
        "graph": "#eef6f2",
        "forecast": "#fff5df",
        "erp": "#eaf0fb",
    }

    for key, (x1, y1, x2, y2, title, subtitle) in boxes.items():
        draw.rounded_rectangle((x1, y1, x2, y2), radius=18, fill=colors[key], outline="#b8c2bf", width=3)
        draw.text((x1 + 24, y1 + 25), title, fill="#1b1f23", font=font_box)
        draw.text((x1 + 24, y1 + 66), subtitle, fill="#52616b", font=font_small)

    arrows = [
        ("ledger", "ocr"),
        ("product", "metric"),
        ("chat", "ner"),
        ("ocr", "graph"),
        ("metric", "graph"),
        ("ner", "graph"),
        ("graph", "erp"),
        ("forecast", "erp"),
    ]
    for start, end in arrows:
        _arrow(draw, _right_mid(boxes[start]), _left_mid(boxes[end]), "#1f7a5b")
    _vertical_arrow(draw, _bottom_mid(boxes["graph"]), _top_mid(boxes["forecast"]), "#1f7a5b")

    draw.text((70, 820), "Viva rule: OCR, product encoder, NER, and forecasting are trained DL. ERP rendering is software orchestration.", fill="#1b1f23", font=font_small)
    img.save(out)
    print(out)


def _has_arial() -> bool:
    return Path("C:/Windows/Fonts/arial.ttf").exists()


def _right_mid(box: tuple[int, int, int, int, str, str]) -> tuple[int, int]:
    return box[2], (box[1] + box[3]) // 2


def _left_mid(box: tuple[int, int, int, int, str, str]) -> tuple[int, int]:
    return box[0], (box[1] + box[3]) // 2


def _bottom_mid(box: tuple[int, int, int, int, str, str]) -> tuple[int, int]:
    return (box[0] + box[2]) // 2, box[3]


def _top_mid(box: tuple[int, int, int, int, str, str]) -> tuple[int, int]:
    return (box[0] + box[2]) // 2, box[1]


def _arrow(draw, start: tuple[int, int], end: tuple[int, int], color: str) -> None:  # type: ignore[no-untyped-def]
    sx, sy = start
    ex, ey = end
    mid = ((sx + ex) // 2, (sy + ey) // 2)
    draw.line((sx, sy, mid[0], sy, mid[0], ey, ex, ey), fill=color, width=4)
    draw.polygon([(ex, ey), (ex - 14, ey - 8), (ex - 14, ey + 8)], fill=color)


def _vertical_arrow(draw, start: tuple[int, int], end: tuple[int, int], color: str) -> None:  # type: ignore[no-untyped-def]
    sx, sy = start
    ex, ey = end
    draw.line((sx, sy, ex, ey), fill=color, width=4)
    draw.polygon([(ex, ey), (ex - 8, ey - 14), (ex + 8, ey - 14)], fill=color)


if __name__ == "__main__":
    main()
