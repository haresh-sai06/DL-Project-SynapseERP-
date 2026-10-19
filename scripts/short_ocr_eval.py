#!/usr/bin/env python3
"""Short CPU OCR train + CER/WER. Writes outputs/metrics/ledger_ocr_metrics.json"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from synapse_erp.models.ocr_architectures import (
    CHAR_TO_INDEX, LedgerCRNN, decode_greedy, encode_text,
)
from synapse_erp.data.synthetic import generate_ledger_lines

def lev(a, b):
    if a == b: return 0
    if not a: return len(b)
    if not b: return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def lev_seq(a, b):
    return lev("\x1f".join(a), "\x1f".join(b))

def make_batch(texts, H=32, W=256):
    imgs, targets, lens = [], [], []
    font = ImageFont.load_default()
    for text in texts:
        text = text.lower()[:60]
        image = Image.new("L", (W, H), color=255)
        ImageDraw.Draw(image).text((4, 4), text, fill=0, font=font)
        arr = np.asarray(image, dtype=np.float32) / 255.0
        imgs.append(torch.from_numpy(arr).unsqueeze(0))
        t = torch.tensor(encode_text(text), dtype=torch.long)
        targets.append(t)
        lens.append(len(t))
    return torch.stack(imgs), torch.cat(targets), torch.tensor(lens, dtype=torch.long)

def main():
    print("start", flush=True)
    torch.manual_seed(42)
    model = LedgerCRNN(num_classes=len(CHAR_TO_INDEX) + 1, hidden_size=48)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    crit = nn.CTCLoss(blank=0, zero_infinity=True)
    epochs, batch_n, batches_per_epoch = 3, 8, 8
    t0 = time.time()
    last_loss = 0.0
    for ep in range(1, epochs + 1):
        model.train()
        total = 0.0
        for b in range(batches_per_epoch):
            lines = generate_ledger_lines(n=batch_n, seed=ep * 1000 + b)
            images, targets, tlen = make_batch(lines)
            opt.zero_grad()
            log_probs = model(images)
            ilen = torch.full((images.size(0),), log_probs.size(0), dtype=torch.long)
            loss = crit(log_probs, targets, ilen, tlen)
            loss.backward()
            opt.step()
            total += float(loss)
        last_loss = total / batches_per_epoch
        print(f"epoch {ep} loss={last_loss:.3f}", flush=True)

    model.eval()
    refs, hyps = [], []
    with torch.no_grad():
        for text in generate_ledger_lines(n=32, seed=777):
            text = text.lower()[:60]
            images, _, _ = make_batch([text])
            hyp = decode_greedy(model(images))[0]
            refs.append(text)
            hyps.append(hyp)
    cer = sum(lev(r, h) for r, h in zip(refs, hyps)) / max(sum(len(r) for r in refs), 1)
    wer = sum(lev_seq(r.split(), h.split()) for r, h in zip(refs, hyps)) / max(sum(len(r.split()) for r in refs), 1)
    metrics = {
        "final_ctc_loss": round(last_loss, 4),
        "cer": round(cer, 4),
        "wer": round(wer, 4),
        "samples_trained_approx": epochs * batches_per_epoch * batch_n,
        "epochs": epochs,
        "eval_samples": len(refs),
        "example_ref": refs[0][:80],
        "example_hyp": hyps[0][:80],
        "elapsed_s": round(time.time() - t0, 1),
        "note": "SHORT CPU run: CRNN-CTC on synthetic ledger lines (H=32,W=256, hidden=48). Not production handwriting OCR.",
    }
    out = ROOT / "outputs" / "metrics" / "ledger_ocr_metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2), flush=True)

if __name__ == "__main__":
    main()
