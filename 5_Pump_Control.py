"""Safe pump control. Demo mode never enables hardware actuation."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from src.hardware_interface import DataSource
from src.predictions import predict_from_reading
from src.safety import evaluate_pump_start
from src.state import safety_config, source_banner_text, sync_hardware_from_settings
from src.ui import apply_theme, banner, configure_page, metric_card, page_header

configure_page("Pump Control")
apply_theme()

page_header(
    "Actuation",
    "Pump control",
    "Manual start requires confirmation. Automatic mode still respects runtime, cooldown, "
    "and sensor-failure locks. Demo mode cannot turn a real pump on.",
)

hardware = sync_hardware_from_settings()
info = hardware.connection_info()
kind, detail = source_banner_text()
demo = hardware.source is DataSource.DEMO

if demo:
    banner(
        "warn",
        "Demo mode — hardware disabled",
        "Manual and automatic commands are evaluated, but the relay is never energized. "
        "Never connect a pump directly to an ESP32 GPIO pin; use a relay and a separate pump supply.",
    )
elif not info.connected:
    banner("error", "ESP32 not connected", detail)
else:
    banner("info", kind, detail)

latest = st.session_state.latest_reading
prediction = None
if latest is not None:
    prediction = predict_from_reading(
        latest,
        model_bundle=st.session_state.active_model,
        moisture_threshold=float(st.session_state.moisture_threshold),
    )

c1, c2, c3 = st.columns(3)
with c1:
    metric_card("Pump", "ON" if hardware.pump_on else "OFF", hardware.last_command_reason, "amber" if hardware.pump_on else "navy")
with c2:
    metric_card(
        "Mode",
        "Automatic" if st.session_state.auto_irrigation else "Manual",
        "Automatic uses the current prediction only when hardware is live.",
        "blue",
    )
with c3:
    metric_card(
        "Safety",
        f"{st.session_state.max_pump_runtime_sec}s max",
        f"Cooldown {st.session_state.cooldown_sec}s · stale-sensor lock enabled",
        "green",
    )

st.session_state.auto_irrigation = st.toggle(
    "Automatic irrigation mode",
    value=bool(st.session_state.auto_irrigation),
    help="If enabled on connected hardware, a 'Required' prediction may start the pump after safety checks.",
)

cfg = safety_config()
moisture = None if latest is None else latest.get("soil_moisture")
last_update = st.session_state.last_update
if hasattr(last_update, "to_pydatetime"):
    last_update = last_update.to_pydatetime()

preview = evaluate_pump_start(
    demo_mode=demo,
    hardware_configured=hardware.hardware_configured,
    hardware_connected=info.connected,
    confirmation=True,
    auto_mode=True,
    last_update=last_update if isinstance(last_update, datetime) else None,
    moisture=None if moisture is None else float(moisture),
    pump_is_on=hardware.pump_on,
    last_stop=hardware.last_stop,
    config=cfg,
)
st.caption(f"Safety preview: {preview.reason}")

if st.session_state.auto_irrigation and prediction is not None and prediction.required:
    decision = hardware.request_pump_on(
        confirmation=True,
        auto_mode=True,
        last_update=last_update if isinstance(last_update, datetime) else None,
        moisture=None if moisture is None else float(moisture),
        safety=cfg,
    )
    if demo:
        banner("demo", "Automatic request blocked", decision.reason)
    elif decision.allowed:
        st.success(decision.reason)
    else:
        banner("warn", "Automatic start blocked", decision.reason)

hardware.enforce_runtime_limit(cfg)

st.subheader("Manual control")
confirm = st.checkbox("I confirm I want to start the water pump.")
disabled = demo or not info.connected or not hardware.hardware_configured
b1, b2 = st.columns(2)
with b1:
    if st.button("Start pump", type="primary", disabled=disabled, use_container_width=True):
        decision = hardware.request_pump_on(
            confirmation=confirm,
            auto_mode=False,
            last_update=last_update if isinstance(last_update, datetime) else None,
            moisture=None if moisture is None else float(moisture),
            safety=cfg,
        )
        if decision.allowed:
            st.success(decision.reason)
        else:
            banner("error", "Pump start rejected", decision.reason)
with b2:
    if st.button("Stop pump", use_container_width=True, disabled=demo):
        hardware.request_pump_off("Pump stopped by user.")
        st.info("Stop command recorded.")

if disabled:
    st.caption("Start remains disabled until Settings marks hardware as configured and a live ESP32 connection exists.")
