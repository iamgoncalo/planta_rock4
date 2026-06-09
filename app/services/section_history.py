"""
PlantaOS — SECTION HISTORY (onda 5a/5d): 1 registo/min por secção.

Memória em processo (7 dias × 14 secções, deque) + persistência Postgres
best-effort. Endpoints lêem da memória (warm-startada da BD ao arranque).
Replay por dia em blocos de 10 min para o twin (treino + pós-mortem).
Retenção: 7 dias — a purga NUNCA é feita por deploy, só por idade.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Optional

_logger = logging.getLogger(__name__)
_LOCK = threading.Lock()

RETENCAO_S = 7 * 24 * 3600.0
MAX_PONTOS = 7 * 24 * 60          # 7 dias a 1/min

# section_id -> deque de registos {ts_ms, ocupacao, fila, espera_prevista_min,
#                                   confianca, a_actual, alertas}
_HIST: dict[str, deque] = {}
_ULTIMO_MIN: int = -1
_PREV_ALERTA: dict[str, Optional[str]] = {}   # transições → decision_log


def record_minute(now_s: Optional[float] = None, force: bool = False) -> int:
    """Grava um registo por secção (no máximo 1/min). Devolve nº gravados."""
    global _ULTIMO_MIN
    t = now_s if now_s is not None else time.time()
    minuto = int(t // 60)
    with _LOCK:
        if not force and minuto == _ULTIMO_MIN:
            return 0
        _ULTIMO_MIN = minuto

    try:
        from app.services import fusao_rolante, secoes_mf
        todos = fusao_rolante.get_all(now_s=t)
    except Exception:
        return 0

    gravados = 0
    rows = []
    for sid, p in todos.items():
        fila = float(p.get("fila_estimada") or 0.0)
        alerta = None
        try:
            alerta = secoes_mf.alerta_fila(sid, fila)
            espera = secoes_mf.espera_prevista_min(sid, fila)
        except Exception:
            espera = 0.0
        # auditoria: transição de alerta vai ao decision_log (sem spam)
        if alerta != _PREV_ALERTA.get(sid):
            _PREV_ALERTA[sid] = alerta
            if alerta in ("WARN", "CRIT"):
                try:
                    from app.services import decision_log
                    decision_log.log(
                        tipo=f"alerta_{alerta.lower()}", origem="motor",
                        seccao=sid,
                        depois={"fila": round(fila, 1), "espera_min": espera},
                        justificacao=f"fila/queue_cap acima do limiar {alerta}",
                    )
                except Exception:
                    pass
        rec = {
            "ts_ms": int(minuto * 60 * 1000),
            "ocupacao": float(p.get("ocupacao") or 0.0),
            "fila": fila,
            "espera_prevista_min": espera,
            "confianca": float(p.get("confianca_cruzada") or 0.0),
            "a_actual": float(p.get("a_actual") or 0.0),
            "alertas": [f"{alerta}_FILA"] if alerta else [],
        }
        with _LOCK:
            if sid not in _HIST:
                _HIST[sid] = deque(maxlen=MAX_PONTOS)
            _HIST[sid].append(rec)
        rows.append((sid, rec))
        gravados += 1

    _persist_rows_async(rows)
    return gravados


def query(section_id: str, ts_from_ms: Optional[int] = None,
          ts_to_ms: Optional[int] = None, page: int = 1,
          size: int = 120) -> dict:
    """Página de histórico de uma secção (mais recente primeiro)."""
    sid = section_id.lower()
    with _LOCK:
        items = list(_HIST.get(sid, ()))
    if ts_from_ms is not None:
        items = [r for r in items if r["ts_ms"] >= ts_from_ms]
    if ts_to_ms is not None:
        items = [r for r in items if r["ts_ms"] <= ts_to_ms]
    items = list(reversed(items))
    size = max(1, min(int(size), 1000))
    page = max(1, int(page))
    total = len(items)
    start = (page - 1) * size
    return {
        "section_id": sid,
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, -(-total // size)),
        "registos": items[start:start + size],
    }


def replay_dia(dia: str) -> dict:
    """Série de um dia (YYYY-MM-DD UTC) em blocos de 10 min por secção."""
    try:
        d0 = datetime.strptime(dia, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ValueError(f"dia inválido (YYYY-MM-DD): {dia!r}")
    t0_ms = int(d0.timestamp() * 1000)
    t1_ms = t0_ms + 24 * 3600 * 1000
    bloco_ms = 10 * 60 * 1000

    with _LOCK:
        snapshot = {sid: list(dq) for sid, dq in _HIST.items()}

    seccoes: dict[str, list[dict]] = {}
    for sid, items in snapshot.items():
        blocos: dict[int, list[dict]] = {}
        for r in items:
            if not (t0_ms <= r["ts_ms"] < t1_ms):
                continue
            blocos.setdefault((r["ts_ms"] - t0_ms) // bloco_ms, []).append(r)
        serie = []
        for b in sorted(blocos):
            grupo = blocos[b]
            n = max(len(grupo), 1)
            serie.append({
                "bloco": int(b),
                "ts_ms": t0_ms + int(b) * bloco_ms,
                "ocupacao": round(sum(g["ocupacao"] for g in grupo) / n, 1),
                "fila": round(sum(g["fila"] for g in grupo) / n, 1),
                "espera_prevista_min": round(
                    sum(g["espera_prevista_min"] for g in grupo) / n, 1),
                "confianca": round(sum(g["confianca"] for g in grupo) / n, 3),
                "amostras": len(grupo),
            })
        if serie:
            seccoes[sid] = serie
    return {"dia": dia, "bloco_min": 10, "seccoes": seccoes,
            "total_seccoes": len(seccoes)}


def reset() -> None:
    global _ULTIMO_MIN
    with _LOCK:
        _HIST.clear()
        _ULTIMO_MIN = -1


# ── Persistência Postgres (best-effort, aditiva) ────────────────────────────
def _persist_rows_async(rows: list[tuple[str, dict]]) -> None:
    try:
        from app.db import AsyncSessionLocal
        if AsyncSessionLocal is None or not rows:
            return
        loop = asyncio.get_running_loop()
        loop.create_task(_persist_rows(AsyncSessionLocal, rows))
    except Exception:
        pass


async def _persist_rows(session_factory, rows: list[tuple[str, dict]]) -> None:
    try:
        from sqlalchemy import delete as _delete
        from app.models.db.operations import SectionHistory
        async with session_factory() as session:
            for sid, r in rows:
                session.add(SectionHistory(
                    section_id=sid, ts_ms=r["ts_ms"], ocupacao=r["ocupacao"],
                    fila=r["fila"], espera_prevista_min=r["espera_prevista_min"],
                    confianca=r["confianca"], a_actual=r["a_actual"],
                    alertas=r["alertas"],
                ))
            # retenção 7 dias — purga só por idade, nunca por deploy
            corte = int((time.time() - RETENCAO_S) * 1000)
            await session.execute(
                _delete(SectionHistory).where(SectionHistory.ts_ms < corte))
            await session.commit()
    except Exception as exc:
        _logger.debug("section_history persist erro (ignorado): %s", exc)


async def load_from_db(session_factory) -> None:
    """Warm start: recarrega a memória a partir da BD."""
    try:
        from sqlalchemy import select as _select
        from app.models.db.operations import SectionHistory
        async with session_factory() as session:
            result = await session.execute(
                _select(SectionHistory).order_by(SectionHistory.ts_ms))
            rows = result.scalars().all()
        with _LOCK:
            for row in rows:
                if row.section_id not in _HIST:
                    _HIST[row.section_id] = deque(maxlen=MAX_PONTOS)
                _HIST[row.section_id].append({
                    "ts_ms": row.ts_ms, "ocupacao": row.ocupacao,
                    "fila": row.fila,
                    "espera_prevista_min": row.espera_prevista_min,
                    "confianca": row.confianca, "a_actual": row.a_actual,
                    "alertas": list(row.alertas or []),
                })
        if rows:
            _logger.info("section_history: %d registos recarregados", len(rows))
    except Exception as exc:
        _logger.debug("section_history load erro (ignorado): %s", exc)


async def history_loop(interval_s: float = 60.0) -> None:
    """Loop 1/min: grava o minuto corrente de todas as secções."""
    while True:
        await asyncio.sleep(interval_s)
        try:
            record_minute()
        except Exception as exc:
            _logger.debug("section_history tick erro (ignorado): %s", exc)
