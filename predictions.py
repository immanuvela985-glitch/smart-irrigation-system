"""Irrigation predictions from a trained model, or a clearly labeled demo rule."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.config import DEFAULT_MOISTURE_THRESHOLD, FEATURE_COLUMNS


@dataclass(frozen=True)
class PredictionResult:
    required: bool
    label: str
    source: str
    explanation: str
    model_name: str | None = None
    probability: float | None = None


def demo_rule_predict(
    moisture: float,
    rainfall_mm: float,
    threshold: float = DEFAULT_MOISTURE_THRESHOLD,
) -> PredictionResult:
    required = moisture < threshold and rainfall_mm < 1.5
    return PredictionResult(
        required=required,
        label="Required" if required else "Not Required",
        source="demo_rule",
        explanation=(
            "No trained model is loaded. This is a demo threshold rule "
            f"(moisture < {threshold:.0f}% and rainfall < 1.5 mm), not a machine-learning prediction."
        ),
        model_name=None,
    )


def predict_from_reading(
    reading: dict[str, Any],
    model_bundle: dict[str, Any] | None = None,
    moisture_threshold: float = DEFAULT_MOISTURE_THRESHOLD,
) -> PredictionResult:
    moisture = float(reading["soil_moisture"])
    rainfall = float(reading.get("rainfall_mm", 0.0) or 0.0)

    if not reading.get("valid", True):
        return PredictionResult(
            required=False,
            label="Unavailable",
            source="invalid_sensor",
            explanation="The latest sensor reading is invalid, so irrigation is not recommended automatically.",
        )

    if model_bundle is None:
        return demo_rule_predict(moisture, rainfall, threshold=moisture_threshold)

    features = model_bundle.get("features") or FEATURE_COLUMNS
    missing = [name for name in features if name not in reading]
    if missing:
        return PredictionResult(
            required=False,
            label="Unavailable",
            source="missing_features",
            explanation=f"Cannot run the trained model; missing features: {', '.join(missing)}.",
            model_name=model_bundle.get("result", {}).get("name"),
        )

    row = pd.DataFrame([{name: float(reading[name]) for name in features}])
    pipeline = model_bundle["pipeline"]
    pred = int(pipeline.predict(row)[0])
    probability = None
    if hasattr(pipeline, "predict_proba"):
        try:
            proba = pipeline.predict_proba(row)[0]
            classes = list(pipeline.classes_)
            probability = float(proba[classes.index(1)]) if 1 in classes else float(max(proba))
        except Exception:  # noqa: BLE001
            probability = None

    name = model_bundle.get("result", {}).get("name", "Saved model")
    return PredictionResult(
        required=bool(pred == 1),
        label="Required" if pred == 1 else "Not Required",
        source="trained_model",
        explanation=f"Prediction from the saved {name} pipeline using features: {', '.join(features)}.",
        model_name=name,
        probability=probability,
    )
