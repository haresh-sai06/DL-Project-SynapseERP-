"""Train a small CRNN-CTC OCR baseline on synthetic ledger-line images using BaseTrainer."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from synapse_erp.config import MODEL_DIR, OUTPUT_DIR, RANDOM_SEED
from synapse_erp.data.synthetic import generate_ledger_lines
from synapse_erp.models.ocr_architectures import CHAR_TO_INDEX, LedgerCRNN, encode_text
from synapse_erp.models.base_trainer import BaseTrainer


def train(args: argparse.Namespace) -> dict[str, float]:
    try:
        import torch
        from PIL import Image, ImageDraw, ImageFont
        from torch import nn
        from torch.utils.data import DataLoader, Dataset
    except Exception as exc:
        raise ImportError("Install torch and pillow from requirements.txt before OCR training.") from exc

    class LedgerImageDataset(Dataset):
        def __init__(self, samples: int) -> None:
            self.lines = generate_ledger_lines(n=samples, seed=RANDOM_SEED)
            random.Random(RANDOM_SEED).shuffle(self.lines)
            self.font = ImageFont.load_default()

        def __len__(self) -> int:
            return len(self.lines)

        def __getitem__(self, index: int):  # type: ignore[no-untyped-def]
            text = self.lines[index].lower()
            image = Image.new("L", (args.width, args.height), color=255)
            draw = ImageDraw.Draw(image)
            jitter_y = random.randint(4, 10)
            draw.text((8, jitter_y), text[:90], fill=0, font=self.font)
            pixels = torch.from_numpy(__import__('numpy').asarray(image, dtype='float32')).view(args.height, args.width) / 255.0
            target = torch.tensor(encode_text(text[:90]), dtype=torch.long)
            return pixels.unsqueeze(0), target

    def collate(batch):  # type: ignore[no-untyped-def]
        images, targets = zip(*batch)
        target_lengths = torch.tensor([len(target) for target in targets], dtype=torch.long)
        flat_targets = torch.cat(targets)
        return torch.stack(images), flat_targets, target_lengths

    torch.manual_seed(RANDOM_SEED)
    dataset = LedgerImageDataset(args.samples)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, collate_fn=collate)
    model = LedgerCRNN(num_classes=len(CHAR_TO_INDEX) + 1, hidden_size=args.hidden_size)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.CTCLoss(blank=0, zero_infinity=True)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.joinpath("metrics").mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.joinpath("figures").mkdir(parents=True, exist_ok=True)

    class OCRTrainer(BaseTrainer):
        def train_step(self, batch) -> torch.Tensor:
            images, targets, target_lengths = batch
            log_probs = self.model(images)
            input_lengths = torch.full(
                size=(images.size(0),),
                fill_value=log_probs.size(0),
                dtype=torch.long,
            )
            return self.criterion(log_probs, targets, input_lengths, target_lengths)

        def on_train_end(self) -> dict[str, float]:
            torch.save({"model_state": self.model.state_dict(), "args": vars(args), "vocab": CHAR_TO_INDEX}, MODEL_DIR / "best_ledger_ocr.pt")

            if self.output_dir:
                _plot_losses(self.history["train_loss"], self.output_dir / "figures" / "ledger_ocr_loss.png")

            # Held-out CER / WER on a fresh synthetic sample (same generator, different seed)
            from synapse_erp.models.ocr_architectures import decode_greedy
            eval_metrics = _evaluate_cer_wer(self.model, args, device=next(self.model.parameters()).device)

            metrics = {
                "final_ctc_loss": self.history["train_loss"][-1] if self.history["train_loss"] else 0.0,
                "samples": args.samples,
                **eval_metrics,
            }
            if self.output_dir:
                (self.output_dir / "metrics" / "ledger_ocr_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
            return metrics

    trainer = OCRTrainer(
        model=model,
        optimizer=optimizer,
        criterion=criterion,
        train_loader=loader,
        epochs=args.epochs,
        model_dir=MODEL_DIR,
        output_dir=OUTPUT_DIR,
    )
    
    return trainer.fit()


def _plot_losses(losses: list[float], output_path: Path) -> None:
    import matplotlib.pyplot as plt

    plt.figure(figsize=(7, 4))
    plt.plot(range(1, len(losses) + 1), losses, marker="o", color="#1f7a5b")
    plt.title("CRNN-CTC Ledger OCR Training Loss")
    plt.xlabel("Epoch")
    plt.ylabel("CTC loss")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _levenshtein_seq(a: list, b: list) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _evaluate_cer_wer(model, args, device) -> dict[str, float]:
    """Greedy-decode a fresh synthetic holdout and compute CER / WER."""
    import torch
    from PIL import Image, ImageDraw, ImageFont
    from synapse_erp.config import RANDOM_SEED
    from synapse_erp.data.synthetic import generate_ledger_lines
    from synapse_erp.models.ocr_architectures import decode_greedy

    model.eval()
    lines = generate_ledger_lines(n=max(32, args.samples // 4), seed=RANDOM_SEED + 7)
    font = ImageFont.load_default()
    refs: list[str] = []
    hyps: list[str] = []
    with torch.no_grad():
        for text in lines:
            text = text.lower()[:90]
            image = Image.new("L", (args.width, args.height), color=255)
            draw = ImageDraw.Draw(image)
            draw.text((8, 6), text, fill=0, font=font)
            pixels = torch.from_numpy(__import__('numpy').asarray(image, dtype='float32')).view(args.height, args.width) / 255.0
            batch = pixels.unsqueeze(0).unsqueeze(0).to(device)
            log_probs = model(batch)
            hyp = decode_greedy(log_probs)[0]
            refs.append(text)
            hyps.append(hyp)
    char_err = sum(_levenshtein(r, h) for r, h in zip(refs, hyps))
    char_total = sum(len(r) for r in refs) or 1
    word_err = sum(_levenshtein_seq(r.split(), h.split()) for r, h in zip(refs, hyps))
    word_total = sum(len(r.split()) for r in refs) or 1
    return {
        "cer": round(char_err / char_total, 4),
        "wer": round(word_err / word_total, 4),
        "eval_samples": len(refs),
        "example_ref": refs[0][:80],
        "example_hyp": hyps[0][:80],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--height", type=int, default=48)
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--hidden-size", type=int, default=96)
    parser.add_argument("--lr", type=float, default=1e-3)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(train(parse_args()), indent=2))
