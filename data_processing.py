"""CSV validation, cleaning, and feature-frame preparation."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import FEATURE_COLUMNS, TARGET_COLUMN, TIMESTAMP_COLUMN

REQUIRED_FEATURE_COLUMNS = list(FEATURE_COLUMNS)
OPTIONAL_COLUMNS = (TIMESTAMP_COLUMN, "source", "valid", TARGET_COLUMN)

NUMERIC_LIMITS = {
    "soil_moisture": (0.0, 100.0),
    "soil_temperature": (-5.0, 60.0),
    "air_temperature": (-10.0, 55.0),
    "humidity": (0.0, 100.0),
    "rainfall_mm": (0.0, 200.0),
}


class DataValidationError(ValueError):
    """Raised when an uploaded or loaded dataset cannot be used."""


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    mapped = frame.copy()
    mapped.columns = [str(col).strip().lower().replace(" ", "_") for col in mapped.columns]
    aliases = {
        "moisture": "soil_moisture",
        "soil_moisture_%": "soil_moisture",
        "soil_moisture_percent": "soil_moisture",
        "temp_soil": "soil_temperature",
        "soil_temp": "soil_temperature",
        "air_temp": "air_temperature",
        "temperature": "air_temperature",
        "rh": "humidity",
        "rain": "rainfall_mm",
        "rainfall": "rainfall_mm",
        "irrigation": TARGET_COLUMN,
        "irrigate": TARGET_COLUMN,
        "label": TARGET_COLUMN,
        "time": TIMESTAMP_COLUMN,
        "datetime": TIMESTAMP_COLUMN,
    }
    mapped = mapped.rename(columns={k: v for k, v in aliases.items() if k in mapped.columns})
    return mapped


def validate_sensor_frame(frame: pd.DataFrame, require_target: bool = False) -> pd.DataFrame:
    """Return a cleaned frame or raise DataValidationError."""
    if frame is None or frame.empty:
        raise DataValidationError("The dataset is empty.")

    cleaned = _normalize_columns(frame)
    missing = [col for col in REQUIRED_FEATURE_COLUMNS if col not in cleaned.columns]
    if missing:
        raise DataValidationError(
            "Missing required columns: "
            + ", ".join(missing)
            + f". Expected at least: {', '.join(REQUIRED_FEATURE_COLUMNS)}."
        )

    if require_target and TARGET_COLUMN not in cleaned.columns:
        raise DataValidationError(
            f"Training requires a target column named '{TARGET_COLUMN}' "
            "(1 = irrigation required, 0 = not required)."
        )

    for column, (low, high) in NUMERIC_LIMITS.items():
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
        out_of_range = cleaned[column].dropna()
        if out_of_range.empty:
            raise DataValidationError(f"Column '{column}' has no numeric values.")
        if (out_of_range < low).any() or (out_of_range > high).any():
            raise DataValidationError(
                f"Column '{column}' has values outside the accepted range {low}–{high}."
            )

    if TIMESTAMP_COLUMN in cleaned.columns:
        cleaned[TIMESTAMP_COLUMN] = pd.to_datetime(cleaned[TIMESTAMP_COLUMN], errors="coerce")

    if TARGET_COLUMN in cleaned.columns:
        cleaned[TARGET_COLUMN] = pd.to_numeric(cleaned[TARGET_COLUMN], errors="coerce")
        valid_labels = set(cleaned[TARGET_COLUMN].dropna().unique())
        if not valid_labels.issubset({0, 1, 0.0, 1.0}):
            raise DataValidationError(
                f"'{TARGET_COLUMN}' must contain only 0/1 labels. Found: {sorted(valid_labels)}."
            )
        cleaned[TARGET_COLUMN] = cleaned[TARGET_COLUMN].astype("Int64")
        if require_target and cleaned[TARGET_COLUMN].nunique(dropna=True) < 2:
            raise DataValidationError(
                "The target column must contain both classes (0 and 1) so the model can be evaluated."
            )

    if "source" not in cleaned.columns:
        cleaned["source"] = "unknown"

    keep = [col for col in [TIMESTAMP_COLUMN, *REQUIRED_FEATURE_COLUMNS, TARGET_COLUMN, "source", "valid"] if col in cleaned.columns]
    cleaned = cleaned[keep].dropna(subset=REQUIRED_FEATURE_COLUMNS)
    if cleaned.empty:
        raise DataValidationError("No usable rows remained after cleaning missing numeric values.")
    return cleaned.reset_index(drop=True)


def load_csv(path: Any, require_target: bool = False) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001 - surface file errors to the UI
        raise DataValidationError(f"Could not read CSV: {exc}") from exc
    return validate_sensor_frame(frame, require_target=require_target)


def descriptive_stats(frame: pd.DataFrame) -> pd.DataFrame:
    numeric = frame[[col for col in REQUIRED_FEATURE_COLUMNS if col in frame.columns]]
    stats = numeric.describe().T
    stats["missing"] = numeric.isna().sum()
    return stats.round(2)


def latest_valid_reading(frame: pd.DataFrame) -> dict[str, Any] | None:
    if frame is None or frame.empty:
        return None
    row = frame.iloc[-1]
    return row.to_dict()
