"""Pump safety interlocks. Demo mode never energizes hardware."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class SafetyConfig:
    max_runtime_sec: int = 20
    cooldown_sec: int = 60
    stale_after_sec: int = 30
    moisture_min: float = 0.0
    moisture_max: float = 100.0


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reason: str
    code: str


def sensor_is_stale(last_update: datetime | None, now: datetime, stale_after_sec: int) -> bool:
    if last_update is None:
        return True
    return (now - last_update) > timedelta(seconds=stale_after_sec)


def moisture_is_valid(value: float | None, config: SafetyConfig) -> bool:
    if value is None:
        return False
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return config.moisture_min <= numeric <= config.moisture_max


def evaluate_pump_start(
    *,
    demo_mode: bool,
    hardware_configured: bool,
    hardware_connected: bool,
    confirmation: bool,
    auto_mode: bool,
    last_update: datetime | None,
    moisture: float | None,
    pump_is_on: bool,
    last_stop: datetime | None,
    now: datetime | None = None,
    config: SafetyConfig | None = None,
) -> SafetyDecision:
    """Decide whether a pump start command may proceed.

    Manual confirmation is required unless auto_mode is True.
    Hardware is never armed in demo mode.
    """
    now = now or datetime.now()
    config = config or SafetyConfig()

    if demo_mode:
        return SafetyDecision(
            False,
            "Pump hardware is disabled in demo mode. This dashboard will not energize a relay or pump.",
            "demo_mode",
        )
    if not hardware_configured:
        return SafetyDecision(
            False,
            "Hardware is not configured. Complete Settings and wiring checks before enabling control.",
            "not_configured",
        )
    if not hardware_connected:
        return SafetyDecision(
            False,
            "No ESP32 connection is available. The pump stays off.",
            "disconnected",
        )
    if pump_is_on:
        return SafetyDecision(False, "Pump is already ON.", "already_on")
    if not auto_mode and not confirmation:
        return SafetyDecision(
            False,
            "Manual pump start requires an explicit confirmation checkbox.",
            "confirmation_required",
        )
    if sensor_is_stale(last_update, now, config.stale_after_sec):
        return SafetyDecision(
            False,
            "Sensor data is missing or stale. Pump start is blocked for safety.",
            "stale_sensor",
        )
    if not moisture_is_valid(moisture, config):
        return SafetyDecision(
            False,
            "Soil moisture reading is invalid. Pump start is blocked.",
            "invalid_sensor",
        )
    if last_stop is not None and (now - last_stop) < timedelta(seconds=config.cooldown_sec):
        remaining = config.cooldown_sec - int((now - last_stop).total_seconds())
        return SafetyDecision(
            False,
            f"Cooldown active. Wait about {max(remaining, 1)} seconds before starting the pump again.",
            "cooldown",
        )
    return SafetyDecision(True, "Safety checks passed.", "ok")


def evaluate_pump_hold(
    *,
    pump_started_at: datetime | None,
    now: datetime | None = None,
    config: SafetyConfig | None = None,
) -> SafetyDecision:
    """Force a stop when maximum runtime is exceeded."""
    now = now or datetime.now()
    config = config or SafetyConfig()
    if pump_started_at is None:
        return SafetyDecision(True, "Pump is not running.", "idle")
    runtime = (now - pump_started_at).total_seconds()
    if runtime >= config.max_runtime_sec:
        return SafetyDecision(
            False,
            f"Maximum pump runtime of {config.max_runtime_sec} seconds reached. Pump must stop.",
            "max_runtime",
        )
    return SafetyDecision(True, "Runtime still within limit.", "ok")
