"""Dashboard home page for the Smart Irrigation System."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.predictions import predict_from_reading
from src.state import format_timestamp, init_state, source_banner_text
from src.ui import apply_theme, banner, configure_page, metric_card, moisture_chart, page_header

configure_page("Dashboard")
apply_theme()
init_state()

page_header(
    "Overview",
    "Farm monitoring dashboard",
    "Soil, weather, irrigation prediction, and pump state in one view. "
    "Until an ESP32 is configured, every reading is labeled as demo simulation.",
)

kind, detail = source_banner_text()
if st.session_state.data_source == "demo":
    banner("demo", kind, detail)
elif "NOT CONNECTED" in kind:
    banner("warn", kind, detail)
else:
    banner("info", kind, detail)

if st.session_state.read_error:
    banner("error", "Sensor read error", str(st.session_state.read_error))

latest = st.session_state.latest_reading
history: pd.DataFrame = st.session_state.history

if latest is None:
    st.info("No sensor readings are available yet. Load sample data from the Sensor Data page.")
    st.stop()

prediction = predict_from_reading(
    latest,
    model_bundle=st.session_state.active_model,
    moisture_threshold=float(st.session_state.moisture_threshold),
)
pump_label = "ON" if st.session_state.hardware.pump_on else "OFF"
info = st.session_state.hardware.connection_info()

c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Soil moisture", f"{float(latest['soil_moisture']):.1f}%", "Capacitive sensor (demo or live)", "green")
with c2:
    metric_card("Irrigation prediction", prediction.label, prediction.explanation, "amber" if prediction.required else "blue")
with c3:
    metric_card("Pump status", pump_label, st.session_state.hardware.last_command_reason, "navy")
with c4:
    metric_card("Connection", "Disconnected" if not info.connected else "Connected", info.detail, "blue")

c5, c6, c7, c8 = st.columns(4)
with c5:
    metric_card("Soil temperature", f"{float(latest['soil_temperature']):.1f} °C", "Near-root temperature", "green")
with c6:
    metric_card("Air temperature", f"{float(latest['air_temperature']):.1f} °C", "Ambient temperature", "blue")
with c7:
    metric_card("Humidity", f"{float(latest['humidity']):.1f}%", "Relative humidity", "navy")
with c8:
    rain = float(latest.get("rainfall_mm") or 0)
    metric_card("Rainfall", f"{rain:.1f} mm", "Available in the example dataset", "green")

st.markdown("")
left, right = st.columns((1.55, 1), gap="large")
with left:
    st.plotly_chart(moisture_chart(history.tail(120)), use_container_width=True)
with right:
    st.subheader("Recent readings")
    show = history.tail(8).copy()
    if "timestamp" in show.columns:
        show["timestamp"] = show["timestamp"].map(format_timestamp)
    display_cols = [col for col in show.columns if col in (
        "timestamp", "soil_moisture", "soil_temperature", "air_temperature",
        "humidity", "rainfall_mm", "irrigation_required", "source",
    )]
    st.dataframe(show[display_cols], use_container_width=True, hide_index=True)
    st.caption(f"Last sensor update: {format_timestamp(st.session_state.last_update)}")
    st.caption(st.session_state.model_status)

st.markdown("")
st.caption("College project · AI-Powered Smart Irrigation System Using Machine Learning and IoT")
