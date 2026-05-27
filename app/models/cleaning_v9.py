"""
PlantaOS · Schemas Pydantic v9
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


CleaningStatus = Literal["clean", "in_progress", "needs_cleaning", "urgent"]
Gender = Literal["M", "F", "U"]


# ════════════════════════════════════════════════════════════════════
# Cleaning v9 — 14 unidades operacionais
# ════════════════════════════════════════════════════════════════════
class UnitCleaningStatus(BaseModel):
    """Estado de uma unidade operacional WC."""
    unit_id: str            # "WC-04_M" ou "WC-05" (unissex)
    cluster_id: str         # "WC-04"
    gender: Gender
    label: str              # "WC-04 Masculino"
    capacity_simultaneous: int   # MASC ou FEM do XLSX
    capacity_total: float        # TOTAL do XLSX (com espera)
    espera: float                # ESPERA do XLSX
    note: str = ""               # ex: "UNISSEX"
    status: CleaningStatus
    last_cleaned_at: Optional[datetime] = None
    minutes_since_clean: Optional[int] = None
    last_team: Optional[str] = None
    last_operator: Optional[str] = None


class CleaningScheduleV9Response(BaseModel):
    """Resposta agregada de todas as 14 unidades."""
    units: list[UnitCleaningStatus]
    total_units: int
    clean_count: int
    needs_count: int
    urgent_count: int
    generated_at: datetime


class WCUnitDefinition(BaseModel):
    """Definição estática de uma unidade (do XLSX)."""
    unit_id: str
    cluster_id: str
    gender: Gender
    label: str
    masc: int
    fem: int
    espera: float
    total: float
    note: str = ""


class WCUnitsCatalog(BaseModel):
    """Catálogo das 14 unidades + totais oficiais."""
    units: list[WCUnitDefinition]
    total_count: int
    total_masc: int
    total_fem: int
    total_espera: float
    total_capacity: float
    source: str = "RIRLX_limiteocupacaobanheiros.xlsx"


# ════════════════════════════════════════════════════════════════════
# SCOR History
# ════════════════════════════════════════════════════════════════════
class ScorRecord(BaseModel):
    ts: float
    iso: str
    status: int
    duration_ms: int
    kpi_01: int
    kpi_02: float
    kpi_03: int
    kpi_04: int
    cluster_count: int
    error: Optional[str] = None


class ScorRecentResponse(BaseModel):
    records: list[ScorRecord]
    count: int


class ScorStats(BaseModel):
    total_publications: int
    ok_count: int
    error_count: int
    success_rate_pct: float
    buffered_entries: int
    last_5min_count: int
    avg_latency_ms_5min: float


class ScorOverview(BaseModel):
    stats: ScorStats
    latest: Optional[ScorRecord] = None
    config: dict
    generated_at: datetime
