from __future__ import annotations
from pydantic import BaseModel

# Re-export from sections for convenience
from app.models.sections import GlobalKPIs, SectionState, LivePayload  # noqa: F401


class ScorTelemetryPayload(BaseModel):
    """Telemetry payload from SCOR (LilyGO) devices.

    GPS coordinates are STATIC metadata — never in recurring telemetry.
    No CO2, temperature, or humidity fields (Rule 7).
    """
    cluster_id: str
    fila_actual: int
    tempo_espera_min: float
    fluxo_entrada_pmin: float
    ocupacao_pct: float
    # GPS intentionally omitted from recurring telemetry
