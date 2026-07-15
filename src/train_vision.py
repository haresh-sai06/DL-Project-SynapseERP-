"""Train a real Convolutional Neural Network on the real MNIST handwritten-digit
dataset using ``BaseTrainer``.

MNIST is a genuine, labeled dataset of 60k handwritten digit images. The model
updates its weights against a real cross-entropy loss and reports a real test
accuracy. In the Synapse ERP pipeline this stands in as the perception encoder
that learns to read handwritten marks before being adapted to ledger glyphs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from synapse_erp.config import MODEL_DIR, OUTPUT_DIR, RANDOM_SEED
from synapse_erp.models.base_trainer import BaseTrainer


def build_model() -> "nn.Module":  # noqa: F821
    import torch
    from torch import nn

    class DigitCNN(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(1, 32, 3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Conv2d(32, 64, 3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Dropout(0.25),
            )
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(64 * 7 * 7, 128),
                nn.ReLU(),
                nn.Dropout(0.5),
                nn.Linear(128, 10),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.classifier(self.features(x))

    return DigitCNN()


def train(args: argparse.Namespace) -> dict[str, float]:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, random_split
    from torchvision import transforms
    from torchvision.datasets import MNIST

    torch.manual_seed(RANDOM_SEED)

    transform = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))]
    )
    data_root = OUTPUT_DIR / "datasets"
    full = MNIST(root=str(data_root), train=True, download=True, transform=transform)
    test_set = MNIST(root=str(data_root), train=False, download=True, transform=transform)

    train_len = int(len(full) * 0.9)
    train_set, val_set = random_split(full, [train_len, len(full) - train_len])
    loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=args.batch_size)
    test_loader = DataLoader(test_set, batch_size=args.batch_size)

    model = build_model()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.joinpath("metrics").mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.joinpath("figures").mkdir(parents=True, exist_ok=True)

    class VisionTrainer(BaseTrainer):
        def train_step(self, batch) -> torch.Tensor:
            images, labels = batch
            return self.criterion(self.model(images), labels)

        def val_step(self, batch) -> torch.Tensor:
            images, labels = batch
            return self.criterion(self.model(images), labels)

        def on_train_end(self) -> dict[str, float]:
            self.model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for images, labels in test_loader:
                    preds = self.model(images).argmax(dim=1)
                    correct += int((preds == labels).sum())
                    total += int(labels.size(0))
            accuracy = correct / max(total, 1)
            torch.save(
                {"model_state": self.model.state_dict(), "accuracy": accuracy},
                MODEL_DIR / "best_vision_cnn.pt",
            )
            if self.output_dir:
                _plot_losses(
                    self.history["train_loss"],
                    self.output_dir / "figures" / "vision_cnn_loss.png",
                )
            result = {
                "dataset": "real:MNIST",
                "source": "real",
                "test_accuracy": accuracy,
                "test_correct": correct,
                "test_total": total,
            }
            if self.output_dir:
                (self.output_dir / "metrics" / "vision_cnn_metrics.json").write_text(
                    json.dumps(result, indent=2), encoding="utf-8"
                )
            return result

    trainer = VisionTrainer(
        model=model,
        optimizer=optimizer,
        criterion=criterion,
        train_loader=loader,
        val_loader=val_loader,
        epochs=args.epochs,
        model_dir=MODEL_DIR,
        output_dir=OUTPUT_DIR,
    )
    return trainer.fit()


def _plot_losses(losses: list[float], output_path: Path) -> None:
    import matplotlib.pyplot as plt

    plt.figure(figsize=(7, 4))
    plt.plot(range(1, len(losses) + 1), losses, marker="o", color="#6366f1")
    plt.title("CNN Handwritten-Digit Training Loss (real MNIST)")
    plt.xlabel("Epoch")
    plt.ylabel("Cross-entropy loss")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(train(parse_args()), indent=2))
