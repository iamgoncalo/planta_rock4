from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, field_validator

SensorSourceType = Literal["ir_entry", "ir_exit", "wifi", "camera", "lorawan", "manual"]


class IRReading(BaseModel):
    source_id: str
    ts: float
    count: int
    direction: Literal["in", "out"]
    confidence: float
    simulated: bool

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        return v


class WiFiAggregateReading(BaseModel):
    """Aggregate WiFi probe count — NO mac addresses, no individual tracking."""
    source_id: str
    ts: float
    devices_raw: int
    people_estimate: int
    calibration_factor: float = 2.5
    simulated: bool
    # mac field intentionally omitted


class CameraMLReading(BaseModel):
    source_id: str
    ts: float
    count: int
    confidence: float
    zone: str
    simulated: bool

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        return v


class LoRaWANStatus(BaseModel):
    device_id: str
    last_seen_ts: Optional[float] = None
    available: bool
    last_packet: Optional[str] = None


class SensorHealth(BaseModel):
    cluster_id: str
    lilygo_online: bool
    lilygo_last_seen: Optional[float] = None
    ir_entry_online: bool
    ir_exit_online: bool
    wifi_online: bool
    camera_online: bool
    lorawan_available: bool
    active_sources: list[str]
    confidence: float
    issues: list[str]
    last_update_ts: float
    simulated: bool

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        return v


class DeviceHealth(BaseModel):
    device_id: str
    device_type: str
    online: bool
    last_seen_ts: Optional[float] = None
    uptime_s: Optional[float] = None
    packet_status: Optional[str] = None
