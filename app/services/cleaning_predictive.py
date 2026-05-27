"""
PlantaOS · Cleaning Predictive Scheduler
==========================================
Gera calendário FUTURO de limpezas com atribuição automática de pessoas.

Estratégia:
  - 14 unidades operacionais (cluster × género ou unissex)
  - Cada unidade limpa 1× por hora (cadência alvo)
  - Round-robin pelas pessoas DA EQUIPA ACTIVA naquela hora
  - Tempo médio por limpeza: 8 minutos (numa unidade)
  - Próximas 24h sempre planeadas

Para responder ao endpoint /cleaning/calendar.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.wc_units import WC_UNITS
from app.services.cleaning_staff import STAFF, active_team_at_hour, by_team


@dataclass
class ScheduledClean:
    """Slot agendado para uma limpeza."""
    slot_id: str            # "WC-04_M_2026-05-28T22:00"
    unit_id: str
    cluster_id: str
    unit_label: str
    gender: str             # "M" | "F" | "U"
    scheduled_for_iso: str  # ISO 8601 UTC
    expected_duration_min: int
    person_id: str | None
    person_name: str | None
    person_phone: str | None
    team: str | None
    status: str             # "planned" | "in_progress" | "done" | "overdue"


def build_24h_schedule(now: datetime | None = None) -> list[ScheduledClean]:
    """Constrói o calendário das próximas 24h.

    Para cada hora H (0–23 contadas a partir de agora):
      - Equipa activa naquela H
      - Round-robin pelos 14 units × 4 pessoas da equipa
      - Cada slot 8 min, espaçados de modo a caber 14 limpezas/h
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Arredondar para hora certa em baixo
    base = now.replace(minute=0, second=0, microsecond=0)
    schedule: list[ScheduledClean] = []

    units = list(WC_UNITS)  # 14 units

    for h_offset in range(24):
        slot_hour = base + timedelta(hours=h_offset)
        team_letter = active_team_at_hour(slot_hour.hour)
        team_members = by_team(team_letter)
        if not team_members:
            continue

        # Distribuir 14 unidades pelas 4 pessoas da equipa, dentro da hora
        # Cada pessoa faz ~3.5 unidades/h → 4 cada com round-robin
        # Espaçamento: 60min / 14units ≈ 4.3min entre slots (mas duração=8min, há sobreposição entre membros — OK)
        for idx, unit in enumerate(units):
            person = team_members[idx % len(team_members)]
            slot_minute = int((idx * 60) / len(units))  # 0, 4, 8, 12, ..., ~55
            slot_dt = slot_hour + timedelta(minutes=slot_minute)

            # Status: passado=done, agora=in_progress, futuro=planned
            delta_min = (slot_dt - now).total_seconds() / 60.0
            if delta_min < -10:
                status = "done"
            elif -10 <= delta_min <= 0:
                status = "in_progress"
            elif delta_min < 60 and h_offset == 0:
                status = "planned"
            else:
                status = "planned"

            schedule.append(ScheduledClean(
                slot_id=f"{unit.unit_id}_{slot_dt.strftime('%Y-%m-%dT%H:%M')}",
                unit_id=unit.unit_id,
                cluster_id=unit.cluster_id,
                unit_label=unit.label,
                gender=unit.gender,
                scheduled_for_iso=slot_dt.isoformat(),
                expected_duration_min=8,
                person_id=person.person_id,
                person_name=person.name,
                person_phone=person.phone,
                team=team_letter,
                status=status,
            ))

    # Ordenar cronologicamente
    schedule.sort(key=lambda s: s.scheduled_for_iso)
    return schedule


def next_slots_by_unit(schedule: list[ScheduledClean], n_per_unit: int = 3) -> dict[str, list[dict[str, Any]]]:
    """Devolve para cada unit_id os próximos N slots PLANNED."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for s in schedule:
        if s.status not in ("planned", "in_progress"):
            continue
        if s.unit_id not in grouped:
            grouped[s.unit_id] = []
        if len(grouped[s.unit_id]) < n_per_unit:
            grouped[s.unit_id].append(asdict(s))
    return grouped
