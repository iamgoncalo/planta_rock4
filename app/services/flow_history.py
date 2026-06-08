"""
PlantaOS — background task de snapshots de fluxo + seed de perfis de multidão.
flush_snapshot_loop(): grava 14 secções a cada 60s nos dias de festival.
seed_crowd_profiles_if_empty(): popula crowd_profiles com surge factors por hora.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta

_logger = logging.getLogger(__name__)

# Dias de festival — UTC (os shows terminam a ~01h UTC+1)
FESTIVAL_DAYS = frozenset([
    date(2026, 6, 20), date(2026, 6, 21),
    date(2026, 6, 27), date(2026, 6, 28),
])


def _festival_day(dt: datetime):
    """Hora < 5 UTC conta como dia anterior (noite do festival)."""
    d = dt.date()
    if dt.hour < 5:
        d = d - timedelta(days=1)
    return d if d in FESTIVAL_DAYS else None


async def _flush_once() -> None:
    from app.routers.flow import get_flow_snapshot
    from app.db import AsyncSessionLocal
    from app.models.db.flow_history import FlowSnapshot

    if AsyncSessionLocal is None:
        return

    snapshot = get_flow_snapshot()
    secoes = snapshot.get("secoes", [])
    if not secoes:
        return

    now = datetime.utcnow()
    fday = _festival_day(now)
    if fday is None:
        return  # fora dos dias de festival

    hour = now.hour
    rows = [
        FlowSnapshot(
            festival_day=fday,
            hour=hour,
            cluster_id=s["cluster_id"],
            secao=s["secao"],
            ocupacao_pct=s.get("ocupacao_pct"),
            fluxo_entrada=s.get("fluxo_entrada_pmin"),
            fluxo_saida=s.get("fluxo_saida_pmin"),
            fila=s.get("fila_actual"),
            confianca_pct=s.get("confianca_pct"),
        )
        for s in secoes
    ]
    async with AsyncSessionLocal() as session:
        session.add_all(rows)
        await session.commit()
    _logger.debug("flush_snapshot: %d rows · dia=%s h=%d", len(rows), fday, hour)


async def flush_snapshot_loop() -> None:
    """Grava snapshot de todas as secções a cada 60s nos dias de festival."""
    while True:
        await asyncio.sleep(60)
        try:
            await _flush_once()
        except Exception as exc:
            _logger.warning("flush_snapshot error: %s", exc)


# ── Perfis de multidão Rock in Rio Lisboa 2026 ──────────────────────────────
# Surge factor: proporção de afluência vs. hora de base.
# Valores calibrados com os perfis típicos de RiRL (2012–2024).

_CROWD_PROFILES = [
    # (festival_day, hour, show_name, palco, expected_attendance, surge_factor)
    # Dia 1 — Sáb 20 Jun
    (date(2026, 6, 20), 14, "Rock Street Opening",        "Rock Street",       8_000,  1.1),
    (date(2026, 6, 20), 16, "Electronic Valley Tarde",    "Electronic Valley", 10_000, 1.3),
    (date(2026, 6, 20), 18, "Palco Sunset Act 1",         "Palco Sunset",      18_000, 1.7),
    (date(2026, 6, 20), 20, "Palco Sunset Headliner",     "Palco Sunset",      28_000, 2.2),
    (date(2026, 6, 20), 22, "Palco Mundo Headliner",      "Palco Mundo",       48_000, 3.0),
    (date(2026, 6, 20),  0, "Late Night Electronic",      "Electronic Valley", 14_000, 1.4),
    # Dia 2 — Dom 21 Jun
    (date(2026, 6, 21), 15, "Rock Street Tarde",          "Rock Street",        7_500, 1.1),
    (date(2026, 6, 21), 17, "Palco Sunset Abertura",      "Palco Sunset",      15_000, 1.5),
    (date(2026, 6, 21), 19, "Palco Mundo Warm-up",        "Palco Mundo",       32_000, 2.4),
    (date(2026, 6, 21), 21, "Palco Mundo Headliner",      "Palco Mundo",       52_000, 3.2),
    (date(2026, 6, 21), 23, "Electronic Closing",         "Electronic Valley", 16_000, 1.5),
    # Dia 3 — Sáb 27 Jun
    (date(2026, 6, 27), 14, "Rock Street Opening",        "Rock Street",        9_000, 1.2),
    (date(2026, 6, 27), 17, "Palco Sunset Act",           "Palco Sunset",      20_000, 1.8),
    (date(2026, 6, 27), 19, "Palco Mundo Warm-up",        "Palco Mundo",       35_000, 2.5),
    (date(2026, 6, 27), 21, "Palco Mundo Headliner",      "Palco Mundo",       54_000, 3.3),
    (date(2026, 6, 27), 23, "Late Night Electronic",      "Electronic Valley", 22_000, 1.8),
    # Dia 4 — Dom 28 Jun (encerramento)
    (date(2026, 6, 28), 15, "Rock Street Final",          "Rock Street",        8_500, 1.2),
    (date(2026, 6, 28), 18, "Palco Sunset Final",         "Palco Sunset",      24_000, 2.1),
    (date(2026, 6, 28), 20, "Palco Mundo Warm-up Final",  "Palco Mundo",       40_000, 2.8),
    (date(2026, 6, 28), 22, "Palco Mundo Encerramento",   "Palco Mundo",       58_000, 3.5),
    (date(2026, 6, 28),  0, "Encerramento Electronic",    "Electronic Valley", 20_000, 1.7),
]


async def seed_crowd_profiles_if_empty(session_factory) -> None:
    """Insere os perfis de multidão se a tabela estiver vazia."""
    from app.models.db.flow_history import CrowdProfile
    from sqlalchemy import select, func as sqlfunc

    if session_factory is None:
        return
    async with session_factory() as session:
        count = (await session.execute(
            select(sqlfunc.count(CrowdProfile.id))
        )).scalar_one()
        if count > 0:
            return
        rows = [
            CrowdProfile(
                festival_day=fday, hour=hour,
                show_name=show, palco=palco,
                expected_attendance=att, surge_factor=surge,
            )
            for fday, hour, show, palco, att, surge in _CROWD_PROFILES
        ]
        session.add_all(rows)
        await session.commit()
    _logger.info("crowd_profiles: %d perfis inseridos", len(_CROWD_PROFILES))
