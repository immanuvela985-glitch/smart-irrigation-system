"""Live monitoring page with labeled demo or hardware readings."""

from __future__ import annotations

import time
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from src.hardware_interface import DataSource
from src.predictions import predict_from_reading
from src.state import append_reading, format_timestamp, safety_config, source_banner_text, sync_hardware_from_settings
from src.ui import apply_theme, banner, configure_page, empty_state, metric_card, moisture_chart, page_header

configure_page("Live Monitoring")
apply_theme()

page_header(
    "Telemetry",
    "Live monitoring",
    "Watch soil moisture change over time. Demo ticks are generated in software. "
    "ESP32 values appear only after a successful serial or Wi-Fi read.",
)

kind, detail = source_banner_text()
if st.session_state.data_source == DataSource.DEMO.value:
    banner("demo", kind, detail)
elif "NOT CONNECTED" in kind:
    banner("warn", kind, detail)
else:
    banner("info", kind, detail)

controls = st.columns((1, 1, 1, 2))
with controls[0]:
    auto = st.toggle("Auto-advance demo", value=False, disabled=st.session_state.data_source != DataSource.DEMO.value)
with controls[1]:
    take_reading = st.button("Take reading", type="primary", use_container_width=True)
with controls[2]:
    st.caption("Demo auto-advance adds one simulated sample every rerun.")

hardware = sync_hardware_from_settings()

if take_reading or (auto and st.session_state.data_source == DataSource.DEMO.value):
    try:
        reading = hardware.read_sensor()
        append_reading(reading)
    except Exception as exc:  # noqa: BLE001
        st.session_state.read_error = str(exc)
        banner("error", "Could not read a sensor value", str(exc))
    else:
        st.session_state.read_error = None

latest = st.session_state.latest_reading
if latest is None:
    empty_state("No readings yet", "Press Take reading or load the example dataset.")
    st.stop()

last_update = st.session_state.last_update
now = datetime.now()
source_value = str(latest.get("source", "unknown"))
if source_value in {"serial", "wifi"} and last_update is not None:
    ts = last_update.to_pydatetime() if hasattr(last_update, "to_pydatetime") else last_update
    if isinstance(ts, datetime) and (now - ts) > timedelta(seconds=safety_config().stale_after_sec):
        banner("warn", "Stale hardware reading", "The last ESP32 sample is older than the safety window.")

if source_value == "demo":
    st.caption("Latest sample source: demo simulation.")
elif source_value in {"serial", "wifi"}:
    st.caption(f"Latest sample source: ESP32 {source_value}.")
else:
    banner("warn", "Unknown source", "This row is not labeled as demo or ESP32 telemetry.")

if latest.get("valid") is False:
    banner("error", "Invalid sensor data", "Moisture is outside 0–100%. Automatic irrigation is blocked.")

prediction = predict_from_reading(
    latest,
    model_bundle=st.session_state.active_model,
    moisture_threshold=float(st.session_state.moisture_threshold),
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Soil moisture", f"{float(latest['soil_moisture']):.1f}%", f"Source: {source_value}", "green")
with c2:
    metric_card("Prediction", prediction.label, prediction.explanation, "amber" if prediction.required else "blue")
with c3:
    metric_card("Pump", "ON" if hardware.pump_on else "OFF", hardware.last_command_reason, "navy")
with c4:
    metric_card("Updated", format_timestamp(last_update), prediction.source, "blue")

history: pd.DataFrame = st.session_state.history
st.plotly_chart(moisture_chart(history.tail(80), "Soil moisture over time"), use_container_width=True)

detail_cols = st.columns(4)
for col, key, unit in zip(
    detail_cols,
    ("soil_temperature", "air_temperature", "humidity", "rainfall_mm"),
    ("°C", "°C", "%", "mm"),
):
    with col:
        metric_card(key.replace("_", " ").title(), f"{float(latest.get(key) or 0):.1f} {unit}", "Latest sample", "green")

if auto and st.session_state.data_source == DataSource.DEMO.value:
    st.caption("Simulation is advancing about every two seconds. Turn the toggle off to pause.")
    time.sleep(2)
    st.rerun()
