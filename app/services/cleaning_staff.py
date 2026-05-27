"""
PlantaOS · Cleaning Staff
==========================
Dataset estático de 8 pessoas que constituem 2 equipas de limpeza.
SIMULADO — nomes e contactos fictícios.

Em produção (pós-11 Junho) este dataset virá do scheduling system
da Rock World ou da empresa de limpeza contratada.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CleaningPerson:
    """Pessoa numa equipa de limpeza."""
    person_id: str          # "CL-01"
    name: str
    phone: str              # +351 9XX XXX XXX
    team: str               # "A" ou "B"
    role: str               # "supervisora" | "operador" | "operadora"
    shift: str              # "manhã" | "tarde" | "noite"
    languages: list[str]    # ["PT", "EN"]


# ════════════════════════════════════════════════════════════════════
# DATASET — 8 pessoas em 2 equipas (4+4) — SIMULADO
# ════════════════════════════════════════════════════════════════════
STAFF: list[CleaningPerson] = [
    # ─── EQUIPA A · tarde (12:00-22:00) ───────────────────────────────
    CleaningPerson("CL-01", "Maria Silva",     "+351 962 145 778", "A", "supervisora", "tarde", ["PT", "EN"]),
    CleaningPerson("CL-02", "João Costa",      "+351 933 287 401", "A", "operador",    "tarde", ["PT"]),
    CleaningPerson("CL-03", "Ana Pereira",     "+351 968 112 339", "A", "operadora",   "tarde", ["PT", "ES"]),
    CleaningPerson("CL-04", "Rui Mendes",      "+351 911 444 220", "A", "operador",    "tarde", ["PT"]),

    # ─── EQUIPA B · noite (20:00-04:00) ───────────────────────────────
    CleaningPerson("CL-05", "Carla Fonseca",   "+351 935 776 102", "B", "supervisora", "noite", ["PT", "EN", "FR"]),
    CleaningPerson("CL-06", "Pedro Antunes",   "+351 924 091 553", "B", "operador",    "noite", ["PT"]),
    CleaningPerson("CL-07", "Sofia Reis",      "+351 967 308 819", "B", "operadora",   "noite", ["PT", "EN"]),
    CleaningPerson("CL-08", "Tiago Marques",   "+351 916 552 074", "B", "operador",    "noite", ["PT"]),
]


def by_team(team: str) -> list[CleaningPerson]:
    return [p for p in STAFF if p.team == team]


def by_id(person_id: str) -> CleaningPerson | None:
    for p in STAFF:
        if p.person_id == person_id:
            return p
    return None


def active_team_at_hour(hour: int) -> str:
    """Devolve a equipa activa àquela hora (0-23).

    14:00-22:00 → A
    22:00-06:00 → B
    Fora disso (06:00-14:00) → manutenção mínima, retornamos A.
    """
    if 14 <= hour < 22:
        return "A"
    return "B"
