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


class SensorNode(BaseModel):
    id: str
    type: str
    model: str
    cluster_id: Optional[str] = None
    section_id: Optional[str] = None
    direction: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    hub_id: Optional[str] = None
    gateway_id: Optional[str] = None
    status: Literal["online", "degraded", "offline"] = "online"
    last_seen_ts: Optional[float] = None


class GatewayStatus(BaseModel):
    gateway_id: str
    model: str
    lat: float
    lon: float
    status: Literal["online", "degraded", "offline"]
    last_seen_ts: float
    connected_hubs: list[str]
    packet_loss_pct: float


class BatteryReport(BaseModel):
    hub_id: str
    cluster_id: str
    battery_mah: int
    draw_ma: int
    estimated_days_remaining: float
    last_seen_ts: float
    status: Literal["ok", "low", "critical"]


class CoverageFeature(BaseModel):
    sensor_id: str
    sensor_type: str
    cluster_id: Optional[str] = None
    lat: float
    lon: float
    radius_m: int
    status: str


class CoverageGeoJSON(BaseModel):
    type: str
    features: list[CoverageFeature]


class MaintenanceItem(BaseModel):
    cluster_id: str
    hub_installed: bool
    ir_count_expected: int
    ir_count_installed: int
    wifi_ap_count_expected: int
    wifi_ap_count_installed: int
    camera_count_expected: int
    camera_count_installed: int
    last_inspection_ts: Optional[float] = None
    notes: str
