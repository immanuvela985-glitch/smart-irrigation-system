"""Train, compare, and persist irrigation classifiers without data leakage."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from src.config import FEATURE_COLUMNS, MODELS_DIR, MODEL_CANDIDATES, TARGET_COLUMN
from src.data_processing import DataValidationError, validate_sensor_frame


@dataclass
class ModelResult:
    name: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    confusion: list[list[int]]
    n_train: int
    n_test: int
    features: list[str]
    trained_at: str
    notes: str


def _estimator_for(name: str):
    if name == "Decision Tree":
        return DecisionTreeClassifier(random_state=42, max_depth=6)
    if name == "Random Forest":
        return RandomForestClassifier(
            n_estimators=120,
            random_state=42,
            max_depth=8,
            min_samples_leaf=3,
        )
    if name == "Logistic Regression":
        return LogisticRegression(max_iter=500, random_state=42)
    raise DataValidationError(f"Unknown model: {name}")


def _pipeline_for(name: str) -> Pipeline:
    # Scale inside the pipeline so the scaler is fit on training data only.
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("clf", _estimator_for(name)),
        ]
    )


def _safe_metric(fn, y_true, y_pred) -> float:
    return float(fn(y_true, y_pred, zero_division=0))


def train_and_compare(
    frame: pd.DataFrame,
    test_size: float = 0.25,
    random_state: int = 42,
) -> dict[str, Any]:
    """Fit the three baseline models on a validated frame.

    Returns measured test metrics only. Does not invent scores.
    """
    cleaned = validate_sensor_frame(frame, require_target=True)
    x = cleaned[FEATURE_COLUMNS]
    y = cleaned[TARGET_COLUMN].astype(int)

    if len(cleaned) < 20:
        raise DataValidationError("Need at least 20 labeled rows to train and evaluate models.")

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    results: list[ModelResult] = []
    pipelines: dict[str, Pipeline] = {}
    trained_at = datetime.now().isoformat(timespec="seconds")

    for name in MODEL_CANDIDATES:
        pipe = _pipeline_for(name)
        pipe.fit(x_train, y_train)
        pred = pipe.predict(x_test)
        matrix = confusion_matrix(y_test, pred, labels=[0, 1])
        result = ModelResult(
            name=name,
            accuracy=float(accuracy_score(y_test, pred)),
            precision=_safe_metric(precision_score, y_test, pred),
            recall=_safe_metric(recall_score, y_test, pred),
            f1=_safe_metric(f1_score, y_test, pred),
            confusion=matrix.astype(int).tolist(),
            n_train=int(len(x_train)),
            n_test=int(len(x_test)),
            features=list(FEATURE_COLUMNS),
            trained_at=trained_at,
            notes=(
                "Metrics are from a held-out test split. Example datasets use a moisture/rainfall "
                "labeling rule, so scores describe this dataset rather than real farm performance."
            ),
        )
        results.append(result)
        pipelines[name] = pipe

    ranked = sorted(results, key=lambda item: (item.f1, item.accuracy), reverse=True)
    return {
        "results": results,
        "ranked": ranked,
        "best_name": ranked[0].name,
        "pipelines": pipelines,
        "features": list(FEATURE_COLUMNS),
        "n_rows": int(len(cleaned)),
        "class_balance": {
            "not_required": int((y == 0).sum()),
            "required": int((y == 1).sum()),
        },
        "split": {"test_size": test_size, "random_state": random_state, "stratified": True},
        "labeling_note": (
            "Performance depends on dataset quality and how irrigation_required was labeled. "
            "Do not treat example-data scores as field-validated accuracy."
        ),
    }


def save_model(pipeline: Pipeline, result: ModelResult, directory: Path | None = None) -> Path:
    directory = directory or MODELS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    slug = result.name.lower().replace(" ", "_")
    path = directory / f"{slug}.joblib"
    payload = {
        "pipeline": pipeline,
        "result": asdict(result),
        "features": result.features,
        "target": TARGET_COLUMN,
    }
    joblib.dump(payload, path)
    return path


def save_all_models(training: dict[str, Any], directory: Path | None = None) -> dict[str, str]:
    saved: dict[str, str] = {}
    for result in training["results"]:
        path = save_model(training["pipelines"][result.name], result, directory=directory)
        saved[result.name] = str(path)
    metrics_path = (directory or MODELS_DIR) / "last_metrics.json"
    payload = {
        "best_name": training["best_name"],
        "results": [asdict(item) for item in training["results"]],
        "n_rows": training["n_rows"],
        "class_balance": training["class_balance"],
        "split": training["split"],
        "labeling_note": training["labeling_note"],
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    metrics_path.write_text(_to_json(payload), encoding="utf-8")
    saved["metrics"] = str(metrics_path)
    return saved


def load_model(path: Path) -> dict[str, Any]:
    payload = joblib.load(path)
    if "pipeline" not in payload or "features" not in payload:
        raise DataValidationError("The joblib file is not a Smart Irrigation model bundle.")
    return payload


def list_saved_models(directory: Path | None = None) -> list[Path]:
    directory = directory or MODELS_DIR
    if not directory.exists():
        return []
    return sorted(directory.glob("*.joblib"))


def _to_json(payload: dict[str, Any]) -> str:
    import json

    def default(obj: Any) -> Any:
        if isinstance(obj, (np.floating, np.integer)):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(type(obj))

    return json.dumps(payload, indent=2, default=default)
