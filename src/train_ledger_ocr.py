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
            pixels = torch.tensor(list(image.getdata()), dtype=torch.float32).view(args.height, args.width) / 255.0
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
            
            metrics = {"final_ctc_loss": self.history["train_loss"][-1] if self.history["train_loss"] else 0.0, "samples": args.samples}
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
