"""Searchable sensor table, CSV import/export, and descriptive statistics."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data_processing import DataValidationError, descriptive_stats, load_csv
from src.state import format_timestamp
from src.ui import apply_theme, banner, configure_page, empty_state, moisture_chart, page_header

configure_page("Sensor Data")
apply_theme()

page_header(
    "Records",
    "Sensor data",
    "Browse, search, upload, and download readings. Uploaded files are validated before they replace the table.",
)

history: pd.DataFrame = st.session_state.history
if history is None or history.empty:
    empty_state("No rows to display", "The example dataset should load automatically. Check data/sample_sensor_data.csv.")
    st.stop()

c1, c2 = st.columns((2, 1))
with c1:
    uploaded = st.file_uploader("Replace table with a CSV upload", type=["csv"])
with c2:
    st.download_button(
        "Download current table (CSV)",
        data=history.to_csv(index=False).encode("utf-8"),
        file_name="sensor_readings.csv",
        mime="text/csv",
        use_container_width=True,
    )

if uploaded is not None:
    try:
        incoming = load_csv(uploaded, require_target=False)
        st.session_state.history = incoming
        st.session_state.latest_reading = incoming.iloc[-1].to_dict()
        st.session_state.last_update = incoming.iloc[-1].get("timestamp")
        history = incoming
        st.success(f"Loaded {len(incoming)} validated rows from the upload.")
    except DataValidationError as exc:
        banner("error", "Upload rejected", str(exc))

search = st.text_input("Search in table (source, timestamp, or values)")
view = history.copy()
if search.strip():
    needle = search.strip().lower()
    mask = view.astype(str).apply(lambda col: col.str.lower().str.contains(needle, na=False))
    view = view[mask.any(axis=1)]

if view.empty:
    empty_state("No matching rows", "Clear the search box or try a different term.")
else:
    display = view.copy()
    if "timestamp" in display.columns:
        display["timestamp"] = display["timestamp"].map(format_timestamp)
    st.dataframe(display, use_container_width=True, hide_index=True, height=360)
    st.caption(f"Showing {len(view)} of {len(history)} rows.")

st.subheader("Moisture history")
st.plotly_chart(moisture_chart(history), use_container_width=True)

st.subheader("Descriptive statistics")
st.dataframe(descriptive_stats(history), use_container_width=True)
if "irrigation_required" in history.columns:
    counts = history["irrigation_required"].value_counts(dropna=True)
    st.caption(
        "Label counts in the current table: "
        + ", ".join(f"{int(idx)} → {int(val)}" for idx, val in counts.items())
    )
