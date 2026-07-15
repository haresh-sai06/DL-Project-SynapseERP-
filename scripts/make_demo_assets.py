"""Generate small local image assets for the platform demo."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as exc:
        raise ImportError("Pillow is required. Run `python -m pip install pillow`.") from exc

    root = Path(__file__).resolve().parents[1]
    out = root / "assets" / "demo"
    out.mkdir(parents=True, exist_ok=True)

    font = _font(24)
    small = _font(18)

    ledger = Image.new("RGB", (840, 520), "#f6f0dc")
    draw = ImageDraw.Draw(ledger)
    draw.rectangle((32, 28, 808, 492), outline="#9a8f74", width=3)
    draw.text((58, 54), "Khata Ledger - June", fill="#1b1f23", font=font)
    lines = [
        "2026-06-01  Ramesh   chini      2 kg    Rs 88",
        "2026-06-01  Anita    rice       5 kg    Rs 310",
        "2026-06-02  Salim    parle-g   10 pk    Rs 100",
        "2026-06-03  Kavya    atta       3 kg    Rs 114",
    ]
    y = 120
    for line in lines:
        draw.text((64, y), line, fill="#30302a", font=small)
        draw.line((54, y + 32, 786, y + 32), fill="#d0c5a7", width=2)
        y += 72
    ledger.save(out / "ledger_khata_sample.png")

    products = [
        ("product_sugar.png", "SUGAR", "#f5fbff", "#255f99"),
        ("product_rice.png", "RICE", "#fff9e9", "#1f7a5b"),
        ("product_parle_g.png", "PARLE-G", "#fff2c7", "#b77918"),
    ]
    for filename, label, bg, fg in products:
        image = Image.new("RGB", (420, 420), bg)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((54, 70, 366, 350), radius=28, fill="white", outline="#b8c2bf", width=4)
        draw.rectangle((92, 126, 328, 256), fill=fg)
        draw.text((112, 278), label, fill="#1b1f23", font=font)
        draw.text((112, 316), "reference photo", fill="#5f6f76", font=small)
        image.save(out / filename)

    print(out)


def _font(size: int):
    from PIL import ImageFont

    arial = Path("C:/Windows/Fonts/arial.ttf")
    if arial.exists():
        return ImageFont.truetype(str(arial), size)
    return ImageFont.load_default()


if __name__ == "__main__":
    main()
