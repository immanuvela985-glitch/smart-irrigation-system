"""Sensor and pump interfaces. Hardware stays inert unless explicitly connected.

Never drive a water pump from an ESP32 GPIO pin. Use a relay module and a
separate pump power supply.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from src.safety import SafetyConfig, SafetyDecision, evaluate_pump_hold, evaluate_pump_start
from src.sensor_simulator import SensorSimulator


class DataSource(str, Enum):
    DEMO = "demo"
    SERIAL = "serial"
    WIFI = "wifi"


class SensorReader(Protocol):
    def read(self) -> dict[str, Any]: ...


@dataclass
class ConnectionInfo:
    source: DataSource
    connected: bool
    hardware_configured: bool
    detail: str
    last_error: str | None = None


class DemoSensorReader:
    """Always-available software reader. Readings are labeled source='demo'."""

    def __init__(self) -> None:
        self.simulator = SensorSimulator()

    def read(self) -> dict[str, Any]:
        reading = self.simulator.next_reading()
        reading["source"] = DataSource.DEMO.value
        reading["valid"] = True
        return reading


class SerialSensorReader:
    """USB serial reader for a later ESP32 integration. Does not fake a connection."""

    def __init__(self, port: str = "COM3", baudrate: int = 115200) -> None:
        self.port = port
        self.baudrate = baudrate
        self._serial = None
        self.last_error: str | None = "Serial is not connected."

    def connect(self) -> bool:
        try:
            import serial  # type: ignore
        except ImportError:
            self.last_error = "pyserial is not installed."
            return False
        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=1)
            self.last_error = None
            return True
        except Exception as exc:  # noqa: BLE001
            self._serial = None
            self.last_error = f"Could not open {self.port}: {exc}"
            return False

    def read(self) -> dict[str, Any]:
        if self._serial is None or not getattr(self._serial, "is_open", False):
            raise ConnectionError(self.last_error or "ESP32 serial is not connected.")
        line = self._serial.readline().decode("utf-8", errors="replace").strip()
        if not line:
            raise ConnectionError("No serial data received from the ESP32.")
        return _parse_sensor_line(line, source=DataSource.SERIAL.value)


class WiFiSensorReader:
    """HTTP reader placeholder. Does not claim a live device if the request fails."""

    def __init__(self, url: str = "http://192.168.4.1/sensor") -> None:
        self.url = url
        self.last_error: str | None = "Wi-Fi sensor is not connected."

    def read(self) -> dict[str, Any]:
        try:
            from urllib.request import urlopen

            with urlopen(self.url, timeout=2) as response:  # noqa: S310 - user-configured LAN URL
                raw = response.read().decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"Wi-Fi read failed: {exc}"
            raise ConnectionError(self.last_error) from exc
        return _parse_sensor_line(raw.strip(), source=DataSource.WIFI.value)


def _parse_sensor_line(line: str, source: str) -> dict[str, Any]:
    """Parse CSV or key=value telemetry from firmware.

    Expected example: 42.1,24.0,29.5,61.0,0.0
    order: moisture, soil_temp, air_temp, humidity, rainfall
    """
    if "=" in line:
        parts = {}
        for token in line.split(","):
            if "=" in token:
                key, value = token.split("=", 1)
                parts[key.strip()] = value.strip()
        moisture = float(parts["moisture"])
        soil_temp = float(parts.get("soil_temp", parts.get("soil_temperature", "nan")))
        air_temp = float(parts.get("air_temp", parts.get("air_temperature", "nan")))
        humidity = float(parts["humidity"])
        rain = float(parts.get("rain", parts.get("rainfall_mm", 0)))
    else:
        fields = [item.strip() for item in line.split(",")]
        if len(fields) < 5:
            raise ValueError("Sensor line must contain 5 numeric fields.")
        moisture, soil_temp, air_temp, humidity, rain = (float(item) for item in fields[:5])

    valid = 0.0 <= moisture <= 100.0
    return {
        "timestamp": datetime.now(),
        "soil_moisture": moisture,
        "soil_temperature": soil_temp,
        "air_temperature": air_temp,
        "humidity": humidity,
        "rainfall_mm": rain,
        "source": source,
        "valid": valid,
    }


@dataclass
class HardwareManager:
    source: DataSource = DataSource.DEMO
    serial_port: str = "COM3"
    wifi_url: str = "http://192.168.4.1/sensor"
    hardware_configured: bool = False
    pump_on: bool = False
    pump_started_at: datetime | None = None
    last_stop: datetime | None = None
    last_command_reason: str = "Pump is OFF. Hardware has not been commanded."
    demo_reader: DemoSensorReader = field(default_factory=DemoSensorReader)
    serial_reader: SerialSensorReader | None = None
    wifi_reader: WiFiSensorReader | None = None

    def connection_info(self) -> ConnectionInfo:
        if self.source is DataSource.DEMO:
            return ConnectionInfo(
                source=self.source,
                connected=False,
                hardware_configured=False,
                detail="Demo mode: software simulation only. No ESP32 is connected.",
            )
        if self.source is DataSource.SERIAL:
            reader = self.serial_reader
            ok = reader is not None and reader._serial is not None
            return ConnectionInfo(
                source=self.source,
                connected=bool(ok),
                hardware_configured=self.hardware_configured,
                detail="USB serial selected." if ok else "USB serial selected, but the ESP32 is not connected.",
                last_error=None if ok else (reader.last_error if reader else "Serial reader not created."),
            )
        reader = self.wifi_reader
        return ConnectionInfo(
            source=self.source,
            connected=False,
            hardware_configured=self.hardware_configured,
            detail="Wi-Fi selected. A successful HTTP read is required before this is treated as connected.",
            last_error=reader.last_error if reader else "Wi-Fi reader not created.",
        )

    def read_sensor(self) -> dict[str, Any]:
        if self.source is DataSource.DEMO:
            return self.demo_reader.read()
        if self.source is DataSource.SERIAL:
            if self.serial_reader is None:
                self.serial_reader = SerialSensorReader(self.serial_port)
                self.serial_reader.connect()
            return self.serial_reader.read()
        if self.wifi_reader is None:
            self.wifi_reader = WiFiSensorReader(self.wifi_url)
        return self.wifi_reader.read()

    def request_pump_on(
        self,
        *,
        confirmation: bool,
        auto_mode: bool,
        last_update: datetime | None,
        moisture: float | None,
        safety: SafetyConfig,
        now: datetime | None = None,
    ) -> SafetyDecision:
        info = self.connection_info()
        decision = evaluate_pump_start(
            demo_mode=self.source is DataSource.DEMO,
            hardware_configured=self.hardware_configured,
            hardware_connected=info.connected,
            confirmation=confirmation,
            auto_mode=auto_mode,
            last_update=last_update,
            moisture=moisture,
            pump_is_on=self.pump_on,
            last_stop=self.last_stop,
            now=now,
            config=safety,
        )
        if not decision.allowed:
            self.last_command_reason = decision.reason
            return decision
        # Real firmware command would be sent here only after a live connection.
        self.pump_on = True
        self.pump_started_at = now or datetime.now()
        self.last_command_reason = "Pump ON command accepted by safety checks."
        return decision

    def request_pump_off(self, reason: str = "Pump stopped.") -> SafetyDecision:
        self.pump_on = False
        self.last_stop = datetime.now()
        self.pump_started_at = None
        self.last_command_reason = reason
        return SafetyDecision(True, reason, "stopped")

    def enforce_runtime_limit(self, safety: SafetyConfig, now: datetime | None = None) -> SafetyDecision:
        hold = evaluate_pump_hold(pump_started_at=self.pump_started_at, now=now, config=safety)
        if not hold.allowed and self.pump_on:
            self.request_pump_off(hold.reason)
        return hold
