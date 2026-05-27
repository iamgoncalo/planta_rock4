"""
PlantaOS · Forecast service
============================
Projecta ocupação a 30 min à frente baseado em:
  - Tendência recente (slope das últimas amostras simuladas)
  - Show schedule (surge ~3.8× nos 25 min depois de fim de show)

Sem ML. Determinístico. Sempre devolve um número.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

# Cluster cap (lugares totais por cluster, do XLSX oficial)
CLUSTER_CAPACITY: dict[str, int] = {
    "WC-01": 135,
    "WC-02": 126,
    "WC-03": 102,
    "WC-04": 150,
    "WC-05": 133,
    "WC-06": 208,
    "WC-07": 138,
    "WC-08": 145,
}

# Quanto cada cluster apanha de surge pós-show, em % do delta
# WC-06 absorve ~88% das redirecções, daí estes pesos
SURGE_WEIGHT: dict[str, float] = {
    "WC-01": 0.05,
    "WC-02": 0.04,
    "WC-03": 0.05,
    "WC-04": 0.06,
    "WC-05": 0.08,
    "WC-06": 0.50,   # absorve a maioria do surge
    "WC-07": 0.15,
    "WC-08": 0.07,
}

SURGE_FACTOR = 3.8
SURGE_DURATION_MIN = 25


@dataclass
class ForecastPoint:
    minutes_ahead: int
    ocupacao_pct: float
    confidence: float  # 0-1
    surge_active: bool


@dataclass
class ClusterForecast:
    cluster_id: str
    horizon_min: int
    current_ocupacao_pct: float
    points: list[ForecastPoint]
    peak_ocupacao_pct: float
    peak_at_min: int
    notes: list[str]


def project(
    cluster_id: str,
    current_pct: float,
    trend_slope_per_min: float = 0.0,
    minutes_to_show_end: Optional[int] = None,
    horizon_min: int = 30,
) -> ClusterForecast:
    """Projecta a curva de ocupação."""
    notes: list[str] = []
    points: list[ForecastPoint] = []
    surge_weight = SURGE_WEIGHT.get(cluster_id, 0.1)

    peak_pct = current_pct
    peak_min = 0

    for m in (5, 10, 15, 20, 25, 30):
        if m > horizon_min:
            break
        # Tendência linear
        base = current_pct + trend_slope_per_min * m
        # Surge contribuição
        surge_active = False
        surge_add = 0.0
        if minutes_to_show_end is not None:
            # Se o show acaba dentro de [-5, +25] min em relação a 'm', surge está activo
            t_after_end = m - minutes_to_show_end
            if 0 <= t_after_end <= SURGE_DURATION_MIN:
                surge_active = True
                # Surge intensifica nos primeiros 10 min, decai depois
                intensity = 1.0 - (t_after_end / SURGE_DURATION_MIN)
                surge_add = surge_weight * (SURGE_FACTOR - 1.0) * 100.0 * intensity
        proj = max(0.0, min(100.0, base + surge_add))
        # Confiança decresce com horizonte
        conf = max(0.3, 0.9 - 0.02 * m)
        points.append(
            ForecastPoint(
                minutes_ahead=m,
                ocupacao_pct=round(proj, 1),
                confidence=round(conf, 2),
                surge_active=surge_active,
            )
        )
        if proj > peak_pct:
            peak_pct = proj
            peak_min = m

    if minutes_to_show_end is not None and 0 < minutes_to_show_end <= horizon_min:
        notes.append(
            f"Show termina daqui a {minutes_to_show_end} min · surge previsto"
        )
    if peak_pct > 85:
        notes.append(f"Pico previsto: {peak_pct:.0f}% aos {peak_min} min")

    return ClusterForecast(
        cluster_id=cluster_id,
        horizon_min=horizon_min,
        current_ocupacao_pct=round(current_pct, 1),
        points=points,
        peak_ocupacao_pct=round(peak_pct, 1),
        peak_at_min=peak_min,
        notes=notes,
    )
