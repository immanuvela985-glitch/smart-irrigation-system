"""Generate clearly labeled demo sensor readings. This is not ESP32 hardware."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import (
    DEFAULT_MOISTURE_THRESHOLD,
    FEATURE_COLUMNS,
    SAMPLE_DATA_PATH,
    TARGET_COLUMN,
    TIMESTAMP_COLUMN,
)


def irrigation_label(
    soil_moisture: float,
    rainfall_mm: float,
    moisture_threshold: float = DEFAULT_MOISTURE_THRESHOLD,
) -> int:
    """Example labeling rule used only for sample/demo datasets.

    irrigation_required = 1 when soil is dry and rainfall is negligible.
    This is a teaching label, not a field-validated agronomic model.
    """
    return int(soil_moisture < moisture_threshold and rainfall_mm < 1.5)


class SensorSimulator:
    """Software simulator that produces agricultural-looking time series."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self.step = 0
        self.moisture = 48.0
        self.soil_temp = 24.0
        self.air_temp = 28.0
        self.humidity = 62.0

    def next_reading(self, now: datetime | None = None) -> dict[str, Any]:
        """Advance the simulation by one step and return a labeled demo reading."""
        now = now or datetime.now()
        hour = now.hour + now.minute / 60.0
        diurnal = np.sin((hour - 6) / 24.0 * 2 * np.pi)

        self.air_temp = float(np.clip(29 + 6 * diurnal + self.rng.normal(0, 0.4), 18, 42))
        self.soil_temp = float(np.clip(0.65 * self.soil_temp + 0.35 * (self.air_temp - 3), 16, 36))
        self.humidity = float(np.clip(70 - 12 * diurnal + self.rng.normal(0, 1.5), 25, 95))

        rain = 0.0
        if self.rng.random() < 0.04:
            rain = float(self.rng.uniform(0.4, 8.0))

        dry_drift = -0.35 if rain < 0.2 else 1.8 * min(rain, 6) / 6
        self.moisture = float(np.clip(self.moisture + dry_drift + self.rng.normal(0, 0.25), 8, 92))

        reading = {
            TIMESTAMP_COLUMN: now,
            "soil_moisture": round(self.moisture, 2),
            "soil_temperature": round(self.soil_temp, 2),
            "air_temperature": round(self.air_temp, 2),
            "humidity": round(self.humidity, 2),
            "rainfall_mm": round(rain, 2),
            "source": "demo",
            "valid": True,
            TARGET_COLUMN: irrigation_label(self.moisture, rain),
        }
        self.step += 1
        return reading

    def history_dataframe(
        self,
        hours: int = 72,
        freq_minutes: int = 30,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        """Build a demo history window ending at `end` (default: now)."""
        end = end or datetime.now().replace(second=0, microsecond=0)
        periods = max(hours * 60 // freq_minutes, 8)
        start = end - timedelta(minutes=freq_minutes * (periods - 1))
        rows: list[dict[str, Any]] = []
        sim = SensorSimulator(seed=7)
        for i in range(periods):
            ts = start + timedelta(minutes=freq_minutes * i)
            rows.append(sim.next_reading(now=ts))
        return pd.DataFrame(rows)


def generate_sample_dataset(
    days: int = 7,
    freq_minutes: int = 30,
    seed: int = 21,
) -> pd.DataFrame:
    """Create the bundled example CSV contents."""
    sim = SensorSimulator(seed=seed)
    end = datetime(2026, 10, 26, 18, 0, 0)
    periods = days * 24 * 60 // freq_minutes
    start = end - timedelta(minutes=freq_minutes * (periods - 1))
    rows = [sim.next_reading(now=start + timedelta(minutes=freq_minutes * i)) for i in range(periods)]
    frame = pd.DataFrame(rows)
    frame["source"] = "demo"
    return frame


def write_sample_dataset(path: Path | None = None) -> Path:
    path = path or SAMPLE_DATA_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    generate_sample_dataset().to_csv(path, index=False)
    return path


def reading_to_feature_row(reading: dict[str, Any]) -> dict[str, float]:
    return {name: float(reading[name]) for name in FEATURE_COLUMNS}
