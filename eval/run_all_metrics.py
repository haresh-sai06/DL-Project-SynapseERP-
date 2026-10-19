"""Re-run measurable Synapse ERP DL modules and collect metrics JSON.

Usage (from repo root, with PYTHONPATH=src)::

    python eval/run_all_metrics.py --out outputs/metrics/summary.json

What is measured here
---------------------
* Ledger OCR (synthetic lines): CTC loss, CER, WER
* Demand forecaster (synthetic SKU series): LSTM vs moving-average MAE/RMSE/MAPE/R2
* Optional: forecaster on real USD/INR (--real-fx) if network is available
* Vision CNN on MNIST is heavy; pass --vision to include (reports test accuracy)

Anything that cannot run is recorded as TBD with a reason.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> tuple[int, str]:
    env = {**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(ROOT / "src")}
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="outputs/metrics/summary.json")
    ap.add_argument("--ocr-epochs", type=int, default=5)
    ap.add_argument("--ocr-samples", type=int, default=256)
    ap.add_argument("--forecast-epochs", type=int, default=12)
    ap.add_argument("--real-fx", action="store_true")
    ap.add_argument("--vision", action="store_true")
    args = ap.parse_args()

    summary: dict = {"modules": {}}
    py = sys.executable

    code, out = run([py, "src/train_ledger_ocr.py", "--epochs", str(args.ocr_epochs),
                     "--samples", str(args.ocr_samples), "--batch-size", "8"])
    ocr_path = ROOT / "outputs" / "metrics" / "ledger_ocr_metrics.json"
    if code == 0 and ocr_path.exists():
        summary["modules"]["ledger_ocr"] = json.loads(ocr_path.read_text())
    else:
        summary["modules"]["ledger_ocr"] = {"status": "TBD", "reason": out[-500:], "exit": code}

    code, out = run([py, "src/train_forecaster.py", "--source", "synthetic",
                     "--epochs", str(args.forecast_epochs), "--days", "220"])
    fc_path = ROOT / "outputs" / "metrics" / "forecast_metrics.json"
    if code == 0 and fc_path.exists():
        summary["modules"]["forecast_synthetic"] = json.loads(fc_path.read_text())
    else:
        summary["modules"]["forecast_synthetic"] = {"status": "TBD", "reason": out[-500:], "exit": code}

    if args.real_fx:
        code, out = run([py, "src/train_forecaster.py", "--source", "real",
                         "--epochs", str(args.forecast_epochs), "--years", "3"])
        if code == 0 and fc_path.exists():
            summary["modules"]["forecast_real_usdinr"] = json.loads(fc_path.read_text())
        else:
            summary["modules"]["forecast_real_usdinr"] = {"status": "TBD", "reason": out[-500:], "exit": code}
    else:
        summary["modules"]["forecast_real_usdinr"] = {
            "status": "TBD",
            "reason": "Skipped (pass --real-fx to download Frankfurter/ECB USD-INR history).",
        }

    if args.vision:
        code, out = run([py, "src/train_vision.py", "--epochs", "2", "--batch-size", "128"])
        # vision script prints JSON; also check for saved metrics if any
        # parse last JSON object from stdout
        try:
            # train_vision prints json.dumps at end — find it
            start = out.rfind("{")
            summary["modules"]["vision_mnist"] = json.loads(out[start:]) if start >= 0 and code == 0 else {
                "status": "TBD", "reason": out[-500:], "exit": code
            }
        except Exception as exc:
            summary["modules"]["vision_mnist"] = {"status": "TBD", "reason": str(exc)}
    else:
        summary["modules"]["vision_mnist"] = {
            "status": "TBD",
            "reason": "Skipped in default eval (pass --vision). Previously claimed ~98% needs remeasurement.",
        }

    summary["modules"]["order_ner"] = {
        "status": "TBD",
        "reason": "Only rule fallback is implemented; MuRIL/IndicBERT fine-tune not trained in this environment.",
    }
    summary["modules"]["product_recognition"] = {
        "status": "TBD",
        "reason": "Metric-learning scaffold only; no labelled few-shot eval set run here.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
