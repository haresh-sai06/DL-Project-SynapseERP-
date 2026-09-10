"""Autoencoder architecture for detecting anomalies in ledger data.

Used for identifying potential fraud, entry errors, or unusual business patterns.
"""

from __future__ import annotations

try:
    import torch
    from torch import nn
except Exception:  # pragma: no cover
    torch = None
    nn = None


def require_torch() -> None:
    if torch is None or nn is None:
        raise ImportError("PyTorch is required for Anomaly Autoencoders.")


class LedgerAnomalyAE(nn.Module if nn is not None else object):
    """Autoencoder to reconstruct structured ledger entries.
    
    A high reconstruction error indicates an anomalous record (e.g. quantity is impossibly high,
    price does not match the item embedding).
    """

    def __init__(self, input_dim: int, hidden_dim: int = 32, latent_dim: int = 8) -> None:
        require_torch()
        super().__init__()
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim * 2),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dim, latent_dim)
        )
        
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dim * 2, input_dim)
        )

    def forward(self, x):  # type: ignore[no-untyped-def]
        require_torch()
        latent = self.encoder(x)
        reconstructed = self.decoder(latent)
        return reconstructed

    def compute_anomaly_score(self, x):  # type: ignore[no-untyped-def]
        """Calculate the MSE reconstruction error per sample."""
        require_torch()
        reconstructed = self.forward(x)
        mse_loss = nn.functional.mse_loss(reconstructed, x, reduction='none')
        return mse_loss.mean(dim=1)
