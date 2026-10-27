"""Application settings. These values are configuration, not live hardware state."""

from __future__ import annotations

import streamlit as st

from src.config import FEATURE_COLUMNS
from src.hardware_interface import DataSource
from src.state import saved_model_names, sync_hardware_from_settings, try_load_named_model
from src.ui import apply_theme, banner, configure_page, page_header

configure_page("Settings")
apply_theme()

page_header(
    "Configuration",
    "Settings",
    "Thresholds, data source, and model choice. Changing a dropdown does not mean the ESP32 is connected.",
)

banner(
    "info",
    "Settings vs hardware",
    "Values on this page are stored in the app session. Connection state is shown separately "
    "and stays disconnected until a serial or Wi-Fi read actually succeeds.",
)

st.subheader("Irrigation threshold")
st.session_state.moisture_threshold = st.slider(
    "Soil moisture threshold (%)",
    min_value=10.0,
    max_value=70.0,
    value=float(st.session_state.moisture_threshold),
    help="Used by the demo rule and shown on moisture charts.",
)

st.subheader("Pump safety (applied only if hardware is later enabled)")
c1, c2 = st.columns(2)
with c1:
    st.session_state.max_pump_runtime_sec = st.number_input(
        "Maximum pump runtime (seconds)",
        min_value=5,
        max_value=120,
        value=int(st.session_state.max_pump_runtime_sec),
        step=5,
    )
with c2:
    st.session_state.cooldown_sec = st.number_input(
        "Cooldown after stop (seconds)",
        min_value=10,
        max_value=300,
        value=int(st.session_state.cooldown_sec),
        step=10,
    )

st.subheader("Data source")
st.session_state.data_source = st.radio(
    "Where should new live readings come from?",
    options=[DataSource.DEMO.value, DataSource.SERIAL.value, DataSource.WIFI.value],
    index=[DataSource.DEMO.value, DataSource.SERIAL.value, DataSource.WIFI.value].index(st.session_state.data_source),
    format_func=lambda value: {"demo": "Demo (software simulation)", "serial": "Serial (USB ESP32)", "wifi": "Wi-Fi (ESP32 HTTP)" }[value],
    horizontal=True,
)
c3, c4 = st.columns(2)
with c3:
    st.session_state.serial_port = st.text_input("Serial port", value=st.session_state.serial_port)
with c4:
    st.session_state.wifi_url = st.text_input("Wi-Fi sensor URL", value=st.session_state.wifi_url)

st.subheader("Hardware profile")
st.markdown(
    """
    Planned student hardware (budget under ₹2,000):

    - ESP32 development board
    - Capacitive soil moisture sensor
    - Relay module
    - Low-voltage DC mini water pump

    **Wiring rule:** the pump must be switched by the relay. Do not power the pump from an ESP32 GPIO pin.
    """
)
st.session_state.hardware_configured = st.checkbox(
    "I have wired the relay and pump correctly and want to allow hardware control later.",
    value=bool(st.session_state.hardware_configured),
)

hardware = sync_hardware_from_settings()
info = hardware.connection_info()
st.write(
    {
        "configured_source": hardware.source.value,
        "hardware_configured_flag": hardware.hardware_configured,
        "actually_connected": info.connected,
        "connection_detail": info.detail,
        "last_error": info.last_error,
        "pump_state": "ON" if hardware.pump_on else "OFF",
    }
)

st.subheader("Active model")
available = saved_model_names()
if not available:
    st.caption("No joblib models in the models/ folder yet. Train models on the Machine Learning page.")
else:
    current = st.session_state.active_model_name
    index = available.index(current) if current in available else 0
    choice = st.selectbox("Saved model", available, index=index)
    if st.button("Load selected model"):
        try_load_named_model(choice)
    st.caption(st.session_state.model_status)
    if st.session_state.active_model:
        st.write(
            {
                "features": st.session_state.active_model.get("features", FEATURE_COLUMNS),
                "file_result": st.session_state.active_model.get("result", {}),
            }
        )

if st.button("Clear loaded model (use demo rule)"):
    try_load_named_model(None)
    st.caption(st.session_state.model_status)
