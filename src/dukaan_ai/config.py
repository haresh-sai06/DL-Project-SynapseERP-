"""Project-wide constants."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

RANDOM_SEED = 42

DEFAULT_CURRENCY = "INR"
DEFAULT_FORECAST_HORIZON_DAYS = 7

