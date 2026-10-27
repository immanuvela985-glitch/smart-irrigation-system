"""Compare measured algorithm metrics from the latest successful training run."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from src.config import MODELS_DIR
from src.ui import apply_theme, banner, comparison_chart, configure_page, confusion_heatmap, empty_state, page_header

configure_page("Model Performance")
apply_theme()

page_header(
    "Evaluation",
    "Model performance",
    "Charts show measured test-set metrics from a real training run. "
    "If you have not trained yet, this page stays empty instead of showing placeholder scores.",
)

training = st.session_state.training
metrics_file = MODELS_DIR / "last_metrics.json"

if training is None and metrics_file.exists():
    try:
        payload = json.loads(metrics_file.read_text(encoding="utf-8"))
        training = payload
        st.caption("Showing metrics saved from the last successful training run on disk.")
    except Exception as exc:  # noqa: BLE001
        banner("error", "Could not read saved metrics", str(exc))

if not training:
    empty_state(
        "No measured results yet",
        "Open Machine Learning, load a dataset, and train the three models. "
        "This page will then compare Decision Tree, Random Forest, and Logistic Regression.",
    )
    st.stop()

banner(
    "info",
    "How to read these numbers",
    training.get(
        "labeling_note",
        "Performance depends on dataset quality and the irrigation-labeling method.",
    ),
)

results = training["results"]
st.plotly_chart(comparison_chart(results), use_container_width=True)

st.subheader("Test metrics")
table = pd.DataFrame(results)
keep = [col for col in ("name", "accuracy", "precision", "recall", "f1", "n_train", "n_test", "trained_at") if col in table.columns]
pretty = table[keep].copy()
for col in ("accuracy", "precision", "recall", "f1"):
    if col in pretty.columns:
        pretty[col] = pretty[col].map(lambda value: round(float(value), 3))
st.dataframe(pretty, use_container_width=True, hide_index=True)

st.subheader("Confusion matrices")
cols = st.columns(3)
for column, item in zip(cols, results):
    with column:
        st.plotly_chart(confusion_heatmap(item["confusion"], item["name"]), use_container_width=True)

balance = training.get("class_balance", {})
split = training.get("split", {})
st.markdown(
    f"- Rows used: **{training.get('n_rows', 'n/a')}**  \n"
    f"- Class balance: not required = **{balance.get('not_required', 'n/a')}**, "
    f"required = **{balance.get('required', 'n/a')}**  \n"
    f"- Split: test_size = **{split.get('test_size', 'n/a')}**, stratified = **{split.get('stratified', True)}**  \n"
    f"- Best F1 in this run: **{training.get('best_name', 'n/a')}**"
)
