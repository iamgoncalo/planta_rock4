from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, field_validator, model_validator

# The 14 fixed WC sections — immutable
SECTION_IDS: tuple[str, ...] = (
    "WC-01_M", "WC-01_F",
    "WC-02_M", "WC-02_F",
    "WC-03_M", "WC-03_F",
    "WC-04_M", "WC-04_F",
    "WC-05",
    "WC-06",
    "WC-07_M", "WC-07_F",
    "WC-08_M", "WC-08_F",
)

UNISEX_SECTIONS: frozenset[str] = frozenset({"WC-05", "WC-06"})

SectionStatus = Literal["normal", "warning", "critical", "offline"]
SensorSourceType = Literal["ir", "wifi", "camera", "lorawan", "manual"]


class SensorReading(BaseModel):
    source_id: str
    source_type: SensorSourceType
    ts: float  # unix epoch seconds
    value: float
    confidence: float  # [0, 1]
    simulated: bool = True

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        return v


class SectionState(BaseModel):
    section_id: str
    ocupacao_pct: float = 0.0         # 0–100
    fila_atual: int = 0
    tempo_espera_min: float = 0.0
    fluxo_entrada_pmin: float = 0.0
    status: SectionStatus = "normal"
    simulated: bool = True
    gender: Optional[Literal["M", "F"]] = None
    confianca: float = 0.5            # I-5: sempre presente ∈ [0,1]
    fontes_activas: list[str] = []
    stale: bool = False
    # Fusão rolante (cabeças + WiFi) — presentes quando a secção tem dados
    fila_estimada: Optional[float] = None
    confianca_cruzada: Optional[float] = None
    a_actual: Optional[float] = None
    idade_ancora_s: Optional[float] = None
    nos_online: Optional[int] = None
    flag_anomalia: Optional[bool] = None
    # Secções M/F (onda 6) — espera por dwell, fila vs queue_cap, fecho
    espera_prevista_min: Optional[float] = None
    queue_cap: Optional[float] = None
    alerta_fila: Optional[str] = None        # "WARN" | "CRIT" | None
    fechado: Optional[bool] = None

    @field_validator("section_id")
    @classmethod
    def valid_section(cls, v: str) -> str:
        if v not in SECTION_IDS:
            raise ValueError(f"section_id '{v}' not in fixed 14-section list")
        return v

    @model_validator(mode="after")
    def no_gender_for_unisex(self) -> "SectionState":
        if self.section_id in UNISEX_SECTIONS and self.gender is not None:
            raise ValueError(
                f"section {self.section_id} is unisex — gender field must be null"
            )
        return self


class GlobalKPIs(BaseModel):
    avg_ocupacao_pct: float = 0.0
    total_fila: int = 0
    critical_sections: int = 0
    redirected_count: int = 0
    any_simulated: bool = True


class LivePayload(BaseModel):
    kpis: GlobalKPIs
    sections: list[SectionState]
    alerts: list[str] = []
    last_tick_age_s: float = 0.0
    any_simulated: bool = True
    # Flags de ambiente (chuva/calor/vento) — opcional, nunca parte o /state
    ambiente: Optional[dict] = None
