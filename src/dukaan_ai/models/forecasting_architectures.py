"""Demand forecasting architectures for inventory planning.

Includes a baseline LSTM and an architectural skeleton for 
Temporal Fusion Transformers (TFT).
"""

from __future__ import annotations

import math

try:
    import torch
    from torch import nn
except Exception:  # pragma: no cover
    torch = None
    nn = None


def require_torch() -> None:
    if torch is None or nn is None:
        raise ImportError("PyTorch is required for forecasting architectures.")


class LSTMDemandForecaster(nn.Module if nn is not None else object):
    """Predict next-step SKU demand from a rolling demand window."""

    def __init__(self, input_size: int = 1, hidden_size: int = 48, num_layers: int = 2) -> None:
        require_torch()
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.1,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, x):  # type: ignore[no-untyped-def]
        require_torch()
        output, _ = self.lstm(x)
        return self.head(output[:, -1, :]).squeeze(-1)


class TemporalFusionTransformer(nn.Module if nn is not None else object):
    """TFT Architecture Skeleton for multi-horizon forecasting.
    
    TFT leverages self-attention to combine static covariates, known future inputs, 
    and observed past inputs.
    """

    def __init__(self, static_dim: int, historical_dim: int, future_dim: int, hidden_size: int = 64) -> None:
        require_torch()
        super().__init__()
        self.hidden_size = hidden_size
        
        # Variable Selection Networks (VSNs)
        self.static_vsn = nn.Linear(static_dim, hidden_size)
        self.historical_vsn = nn.Linear(historical_dim, hidden_size)
        self.future_vsn = nn.Linear(future_dim, hidden_size)
        
        # LSTM Encoders/Decoders for local processing
        self.lstm_encoder = nn.LSTM(hidden_size, hidden_size, batch_first=True)
        self.lstm_decoder = nn.LSTM(hidden_size, hidden_size, batch_first=True)
        
        # Multi-head attention for long-term dependencies
        self.attention = nn.MultiheadAttention(embed_dim=hidden_size, num_heads=4, batch_first=True)
        
        # Output layers (quantiles)
        self.quantile_head = nn.Linear(hidden_size, 3) # e.g. p10, p50, p90

    def forward(self, static_feat, historical_feat, future_feat):  # type: ignore[no-untyped-def]
        require_torch()
        # Stub implementation
        # In a real TFT:
        # 1. Pass features through VSNs
        # 2. LSTM encode history
        # 3. LSTM decode future
        # 4. Multi-head attention across time
        # 5. Gating and residual connections
        # 6. Quantile predictions
        
        batch_size = static_feat.size(0)
        seq_len = future_feat.size(1)
        
        # Dummy output representing p10, p50, p90 quantiles
        device = static_feat.device
        return torch.zeros(batch_size, seq_len, 3, device=device)


def make_windows(series: list[float], window: int = 14) -> tuple[list[list[float]], list[float]]:
    x: list[list[float]] = []
    y: list[float] = []
    for idx in range(len(series) - window):
        x.append(series[idx : idx + window])
        y.append(series[idx + window])
    return x, y


def regression_metrics(y_true: list[float], y_pred: list[float]) -> dict[str, float]:
    n = max(len(y_true), 1)
    errors = [pred - true for true, pred in zip(y_true, y_pred)]
    mae = sum(abs(err) for err in errors) / n
    rmse = math.sqrt(sum(err * err for err in errors) / n)
    nonzero = [abs((pred - true) / true) for true, pred in zip(y_true, y_pred) if abs(true) > 1e-6]
    mape = 100.0 * sum(nonzero) / max(len(nonzero), 1)
    mean_true = sum(y_true) / n
    ss_res = sum((true - pred) ** 2 for true, pred in zip(y_true, y_pred))
    ss_tot = sum((true - mean_true) ** 2 for true in y_true) or 1.0
    r2 = 1.0 - ss_res / ss_tot
    return {"mae": mae, "rmse": rmse, "mape": mape, "r2": r2}
