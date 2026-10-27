from datetime import datetime, timedelta

from src.safety import SafetyConfig, evaluate_pump_hold, evaluate_pump_start


def test_demo_mode_never_starts_pump() -> None:
    decision = evaluate_pump_start(
        demo_mode=True,
        hardware_configured=True,
        hardware_connected=True,
        confirmation=True,
        auto_mode=True,
        last_update=datetime.now(),
        moisture=20.0,
        pump_is_on=False,
        last_stop=None,
    )
    assert decision.allowed is False
    assert decision.code == "demo_mode"


def test_manual_start_requires_confirmation() -> None:
    decision = evaluate_pump_start(
        demo_mode=False,
        hardware_configured=True,
        hardware_connected=True,
        confirmation=False,
        auto_mode=False,
        last_update=datetime.now(),
        moisture=20.0,
        pump_is_on=False,
        last_stop=None,
    )
    assert decision.code == "confirmation_required"


def test_stale_and_invalid_sensor_block_start() -> None:
    now = datetime.now()
    stale = evaluate_pump_start(
        demo_mode=False,
        hardware_configured=True,
        hardware_connected=True,
        confirmation=True,
        auto_mode=True,
        last_update=now - timedelta(minutes=5),
        moisture=20.0,
        pump_is_on=False,
        last_stop=None,
        now=now,
    )
    assert stale.code == "stale_sensor"

    invalid = evaluate_pump_start(
        demo_mode=False,
        hardware_configured=True,
        hardware_connected=True,
        confirmation=True,
        auto_mode=True,
        last_update=now,
        moisture=140.0,
        pump_is_on=False,
        last_stop=None,
        now=now,
    )
    assert invalid.code == "invalid_sensor"


def test_max_runtime_forces_stop() -> None:
    started = datetime.now() - timedelta(seconds=25)
    decision = evaluate_pump_hold(pump_started_at=started, config=SafetyConfig(max_runtime_sec=20))
    assert decision.allowed is False
    assert decision.code == "max_runtime"
