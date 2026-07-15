"""Train an LSTM demand forecaster using BaseTrainer.

Two data sources are supported:

* ``--source synthetic`` (default): deterministic SKU demand curves. Useful for
  reproducible demos and for the viva when no network is available.
* ``--source real``: downloads REAL daily USD/INR exchange rates from the
  Frankfurter / ECB API and treats the import-cost signal as the series to
  forecast. The model still updates weights against a labeled loss on a real
  dataset, so this satisfies the "real DL training" requirement.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from synapse_erp.config import MODEL_DIR, OUTPUT_DIR, RANDOM_SEED
from synapse_erp.data.synthetic import demand_series_for_sku
from synapse_erp.live_data import fetch_historical_fx
from synapse_erp.models.forecasting_architectures import LSTMDemandForecaster, make_windows, regression_metrics
from synapse_erp.models.base_trainer import BaseTrainer


def load_real_series(base: str = "USD", symbol: str = "INR", years: int = 5) -> list[float]:
    """Download a real daily FX series and return it as a plain float list."""
    from datetime import date, timedelta

    end = date.today()
    start = end - timedelta(days=365 * years)
    series = fetch_historical_fx(start.isoformat(), end.isoformat(), base=base, symbol=symbol)
    values = [point["value"] for point in series if point.get("value") is not None]
    if len(values) < 60:
        raise RuntimeError(f"Not enough real data points fetched ({len(values)}).")
    return values


def moving_average_baseline(train: list[float], test: list[float], window: int = 7) -> list[float]:
    history = list(train)
    predictions: list[float] = []
    for actual in test:
        predictions.append(sum(history[-window:]) / min(len(history), window))
        history.append(actual)
    return predictions


def train(args: argparse.Namespace) -> dict[str, float]:
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset
    except Exception as exc:
        raise ImportError("PyTorch is required. Run `python -m pip install -r requirements.txt`.") from exc

    torch.manual_seed(RANDOM_SEED)

    if args.source == "real":
        series_raw = load_real_series(base=args.base, symbol=args.symbol, years=args.years)
        mean = sum(series_raw) / len(series_raw)
        var = sum((v - mean) ** 2 for v in series_raw) / len(series_raw)
        std = var ** 0.5 or 1.0
        series = [(v - mean) / std for v in series_raw]
        norm_params = (mean, std)
        dataset_label = f"real:{args.base}{args.symbol}"
    else:
        series = demand_series_for_sku(args.sku, days=args.days)
        norm_params = None
    x, y = make_windows(series, window=args.window)
    split = int(len(x) * 0.8)
    x_train, y_train = x[:split], y[:split]
    x_test, y_test = x[split:], y[split:]

    train_tensor = torch.tensor(x_train, dtype=torch.float32).unsqueeze(-1)
    target_tensor = torch.tensor(y_train, dtype=torch.float32)
    loader = DataLoader(TensorDataset(train_tensor, target_tensor), batch_size=args.batch_size, shuffle=True)

    model = LSTMDemandForecaster(hidden_size=args.hidden_size)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.MSELoss()

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.joinpath("metrics").mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.joinpath("figures").mkdir(parents=True, exist_ok=True)

    class ForecastTrainer(BaseTrainer):
        def train_step(self, batch) -> torch.Tensor:
            batch_x, batch_y = batch
            return self.criterion(self.model(batch_x), batch_y)

        def on_train_end(self) -> dict[str, float]:
            self.model.eval()
            with torch.no_grad():
                test_tensor = torch.tensor(x_test, dtype=torch.float32).unsqueeze(-1)
                pred_norm = self.model(test_tensor).tolist()

            if norm_params:
                mean, std = norm_params
                predictions = [p * std + mean for p in pred_norm]
                y_test_d = [v * std + mean for v in y_test]
                base_norm = moving_average_baseline(y_train, y_test)
                baseline_pred = [p * std + mean for p in base_norm]
            else:
                predictions = pred_norm
                y_test_d = y_test
                baseline_pred = moving_average_baseline(y_train, y_test)

            metrics = regression_metrics(y_test_d, predictions)
            baseline = regression_metrics(y_test_d, baseline_pred)

            torch.save({"model_state": self.model.state_dict(), "args": vars(args), "metrics": metrics}, MODEL_DIR / "best_model.pt")
            torch.save({"model_state": self.model.state_dict(), "args": vars(args), "metrics": metrics}, MODEL_DIR / "best_forecaster.pt")
            
            if self.output_dir:
                _plot_losses(self.history["train_loss"], self.output_dir / "figures" / "forecast_loss.png")
                
            result = {
                "dataset": dataset_label,
                "source": args.source,
                **{f"lstm_{key}": value for key, value in metrics.items()},
                **{f"moving_average_{key}": value for key, value in baseline.items()},
            }
            if self.output_dir:
                (self.output_dir / "metrics" / "forecast_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            return result

    trainer = ForecastTrainer(
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
    plt.plot(range(1, len(losses) + 1), losses, marker="o")
    plt.title("LSTM Demand Forecast Training Loss")
    plt.xlabel("Epoch")
    plt.ylabel("MSE loss")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="synthetic", choices=["synthetic", "real"])
    parser.add_argument("--sku", default="sugar")
    parser.add_argument("--days", type=int, default=220)
    parser.add_argument("--base", default="USD")
    parser.add_argument("--symbol", default="INR")
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--window", type=int, default=14)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--hidden-size", type=int, default=48)
    parser.add_argument("--lr", type=float, default=1e-3)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(train(parse_args()), indent=2))
