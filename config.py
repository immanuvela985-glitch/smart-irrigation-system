"""Application paths, defaults, and shared constants."""

from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
SAMPLE_DATA_PATH = DATA_DIR / "sample_sensor_data.csv"

APP_TITLE = "AI-Powered Smart Irrigation"
APP_SUBTITLE = "Machine Learning and IoT monitoring dashboard"

# Moisture below this percentage is treated as dry in demo settings.
DEFAULT_MOISTURE_THRESHOLD = 35.0
DEFAULT_MAX_PUMP_RUNTIME_SEC = 20
DEFAULT_COOLDOWN_SEC = 60
STALE_READING_SECONDS = 30

FEATURE_COLUMNS = [
    "soil_moisture",
    "soil_temperature",
    "air_temperature",
    "humidity",
    "rainfall_mm",
]
TARGET_COLUMN = "irrigation_required"
TIMESTAMP_COLUMN = "timestamp"
SOURCE_COLUMN = "source"

VALID_SOURCES = ("demo", "serial", "wifi")
MODEL_CANDIDATES = ("Decision Tree", "Random Forest", "Logistic Regression")

NAVY = "#0B1D36"
GREEN = "#1F8A4C"
BLUE = "#1D6FBF"
LIGHT_BG = "#F3F6FB"
