"""
PlantaOS · Pydantic schemas para operações
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ============================================================================
# CLEANING
# ============================================================================
CleaningStatus = Literal["clean", "in_progress", "needs_cleaning", "urgent"]


class CleaningEntry(BaseModel):
    id: int
    cluster_id: str
    cleaned_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    status: CleaningStatus = "clean"
    team: Optional[str] = None
    operator: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class CleaningClusterStatus(BaseModel):
    """Vista agregada por cluster: último estado + próximo agendado."""
    cluster_id: str
    status: CleaningStatus
    last_cleaned_at: Optional[datetime] = None
    next_scheduled_for: Optional[datetime] = None
    last_team: Optional[str] = None
    minutes_since_clean: Optional[int] = None


class CleaningScheduleResponse(BaseModel):
    clusters: list[CleaningClusterStatus]
    generated_at: datetime


class CleaningDoneRequest(BaseModel):
    cluster_id: str
    team: Optional[str] = None
    operator: Optional[str] = None
    notes: Optional[str] = None


class CleaningScheduleRequest(BaseModel):
    cluster_id: str
    scheduled_for: datetime
    team: Optional[str] = None
    notes: Optional[str] = None


# ============================================================================
# STAFF
# ============================================================================
StaffRole = Literal["cleaning", "steward", "medic", "security", "supervisor"]


class StaffEntry(BaseModel):
    id: int
    day: str
    cluster_id: str
    shift_start: str
    shift_end: str
    role: StaffRole
    name: Optional[str] = None
    contact: Optional[str] = None
    confirmed: bool = False
    notes: Optional[str] = None


class StaffRosterResponse(BaseModel):
    day: str
    total: int
    by_cluster: dict[str, list[StaffEntry]]
    by_role: dict[str, int]


class StaffCreateRequest(BaseModel):
    day: str = Field(..., examples=["2026-06-20"])
    cluster_id: str
    shift_start: str = Field(..., examples=["14:00"])
    shift_end: str = Field(..., examples=["18:00"])
    role: StaffRole
    name: Optional[str] = None
    contact: Optional[str] = None
    notes: Optional[str] = None


# ============================================================================
# INCIDENTS
# ============================================================================
IncidentSeverity = Literal["info", "warning", "critical"]
IncidentCategory = Literal[
    "medical", "crowd", "safety", "hygiene", "technical", "other"
]


class IncidentEntry(BaseModel):
    id: int
    cluster_id: Optional[str] = None
    severity: IncidentSeverity
    category: IncidentCategory
    note: str
    reported_by: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_note: Optional[str] = None
    occurred_at: datetime
    created_at: datetime


class IncidentCreateRequest(BaseModel):
    cluster_id: Optional[str] = None
    severity: IncidentSeverity = "info"
    category: IncidentCategory = "other"
    note: str
    reported_by: Optional[str] = None


class IncidentResolveRequest(BaseModel):
    resolved_by: str
    resolution_note: Optional[str] = None


class IncidentListResponse(BaseModel):
    incidents: list[IncidentEntry]
    total: int
    open_count: int
    critical_count: int


# ============================================================================
# WEATHER
# ============================================================================
class WeatherNow(BaseModel):
    location: str = "Lisboa"
    fetched_at: datetime
    valid_until: datetime
    temperature_c: float
    feels_like_c: float
    humidity_pct: float
    wind_kmh: float
    wind_direction_deg: float
    precipitation_mm_h: float
    weather_code: int
    weather_label: str
    source: str = "open-meteo"
