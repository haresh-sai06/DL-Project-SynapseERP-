"""Base training loop abstractions for Deep Learning models.

Provides a unified interface for training, validation, metric logging,
and checkpoint saving, avoiding scattered training scripts.
"""

from __future__ import annotations

import json
from pathlib import Path

try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader
except Exception:  # pragma: no cover
    torch = None
    nn = None
    DataLoader = None


def require_torch() -> None:
    if torch is None or nn is None:
        raise ImportError("PyTorch is required for BaseTrainer. Install requirements.txt first.")


class BaseTrainer:
    """Abstract trainer for PyTorch models."""

    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        criterion: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader | None = None,
        epochs: int = 10,
        model_dir: Path | None = None,
        output_dir: Path | None = None,
    ) -> None:
        require_torch()
        self.model = model
        self.optimizer = optimizer
        self.criterion = criterion
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.epochs = epochs
        self.model_dir = model_dir
        self.output_dir = output_dir

        self.history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}

    def train_step(self, batch) -> torch.Tensor:  # type: ignore[no-untyped-def]
        """To be implemented by subclasses. Should return the computed loss."""
        raise NotImplementedError

    def val_step(self, batch) -> torch.Tensor:  # type: ignore[no-untyped-def]
        """To be implemented by subclasses if val_loader is provided."""
        raise NotImplementedError

    def on_epoch_end(self, epoch: int, train_loss: float, val_loss: float | None) -> None:
        """Hook called at the end of every epoch."""
        pass

    def on_train_end(self) -> dict[str, float]:
        """Hook called at the end of training. Returns final metrics."""
        return {}

    def fit(self) -> dict[str, float]:
        """Runs the main training loop."""
        for epoch in range(1, self.epochs + 1):
            # Training phase
            self.model.train()
            train_running = 0.0
            for batch in self.train_loader:
                self.optimizer.zero_grad()
                loss = self.train_step(batch)
                loss.backward()
                self.optimizer.step()
                train_running += float(loss.item())
                
            train_loss = train_running / max(len(self.train_loader), 1)
            self.history["train_loss"].append(train_loss)

            # Validation phase
            val_loss = None
            if self.val_loader is not None:
                self.model.eval()
                val_running = 0.0
                with torch.no_grad():
                    for batch in self.val_loader:
                        loss = self.val_step(batch)
                        val_running += float(loss.item())
                val_loss = val_running / max(len(self.val_loader), 1)
                self.history["val_loss"].append(val_loss)

            self.on_epoch_end(epoch, train_loss, val_loss)

        return self.on_train_end()
