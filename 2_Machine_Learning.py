"""Train and inspect irrigation classifiers."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import FEATURE_COLUMNS, SAMPLE_DATA_PATH, TARGET_COLUMN
from src.data_processing import DataValidationError, load_csv
from src.model_training import ModelResult, save_all_models, train_and_compare
from src.state import try_load_named_model
from src.ui import apply_theme, banner, comparison_chart, configure_page, confusion_heatmap, empty_state, page_header

configure_page("Machine Learning")
apply_theme()

page_header(
    "Models",
    "Train irrigation classifiers",
    "Upload a labeled CSV or use the bundled example dataset. "
    "Example results are measured on that file only — they are not invented scores.",
)

banner(
    "info",
    "Example data is labeled",
    "The bundled CSV uses a teaching rule: irrigation_required = 1 when soil moisture is below 35% "
    "and rainfall is under 1.5 mm. High scores on example data do not prove field performance.",
)

source = st.radio(
    "Training data",
    ("Bundled example CSV", "Upload CSV"),
    horizontal=True,
)

frame: pd.DataFrame | None = None
load_error = None
try:
    if source == "Bundled example CSV":
        frame = load_csv(SAMPLE_DATA_PATH, require_target=True)
        st.caption(f"Loaded example file: {SAMPLE_DATA_PATH.name} ({len(frame)} rows).")
    else:
        uploaded = st.file_uploader("Upload a labeled sensor CSV", type=["csv"])
        if uploaded is None:
            empty_state(
                "Waiting for a CSV",
                f"Required columns: {', '.join(FEATURE_COLUMNS)} and {TARGET_COLUMN} (0 or 1).",
            )
        else:
            frame = load_csv(uploaded, require_target=True)
            st.success(f"Validated upload: {len(frame)} rows.")
except DataValidationError as exc:
    load_error = str(exc)
    banner("error", "Dataset could not be used", str(exc))

if frame is not None and load_error is None:
    with st.expander("Preview training rows", expanded=False):
        st.dataframe(frame.head(15), use_container_width=True, hide_index=True)

    test_size = st.slider("Test split fraction", 0.15, 0.40, 0.25, 0.05)
    if st.button("Train Decision Tree, Random Forest, and Logistic Regression", type="primary"):
        try:
            training = train_and_compare(frame, test_size=test_size)
            saved = save_all_models(training)
            st.session_state.training = {
                "results": [item.__dict__ if isinstance(item, ModelResult) else item for item in training["results"]],
                "best_name": training["best_name"],
                "n_rows": training["n_rows"],
                "class_balance": training["class_balance"],
                "split": training["split"],
                "labeling_note": training["labeling_note"],
                "features": training["features"],
                "saved": saved,
            }
            try_load_named_model(training["best_name"])
            st.success(
                f"Training finished on {training['n_rows']} rows. "
                f"Best F1 on the test split: {training['best_name']}. Models saved with joblib."
            )
        except Exception as exc:  # noqa: BLE001
            st.session_state.training = None
            banner("error", "Training did not succeed", str(exc))

training = st.session_state.training
if not training:
    empty_state(
        "No training run in this session",
        "Press the train button after a valid dataset is loaded. This page will not display placeholder accuracy.",
    )
    st.stop()

st.subheader("Measured test metrics")
st.caption(training["labeling_note"])
results = training["results"]
st.plotly_chart(comparison_chart(results), use_container_width=True)

table = pd.DataFrame(results)[["name", "accuracy", "precision", "recall", "f1", "n_train", "n_test"]]
for col in ("accuracy", "precision", "recall", "f1"):
    table[col] = table[col].map(lambda value: round(float(value), 3))
st.dataframe(table, use_container_width=True, hide_index=True)

st.subheader("Confusion matrices")
cols = st.columns(3)
for column, item in zip(cols, results):
    with column:
        st.plotly_chart(confusion_heatmap(item["confusion"], item["name"]), use_container_width=True)

st.subheader("Selected model")
choice = st.selectbox("Inspect / activate a trained model", [item["name"] for item in results], index=0)
if st.button("Use this model for dashboard predictions"):
    try_load_named_model(choice)
    st.success(st.session_state.model_status)

selected = next(item for item in results if item["name"] == choice)
st.write(
    {
        "model": selected["name"],
        "input features": training["features"],
        "trained_at": selected["trained_at"],
        "test accuracy": round(selected["accuracy"], 4),
        "notes": selected["notes"],
    }
)
st.caption(st.session_state.model_status)
