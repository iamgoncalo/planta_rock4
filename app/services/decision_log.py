"""
PlantaOS — DECISION LOG (onda 5b): nada acontece sem rasto.

Toda a decisão do motor (alerta, troca de recomendação, pré-surto, modo
degradado) e todo o comando do operador (cluster_fechado/reaberto) ficam
registados com utilizador, timestamp ms UTC, antes/depois e justificação.
Memória em anel (processo) + persistência Postgres best-effort.
RGPD: nunca registar identificadores pessoais — apenas utilizador operacional.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Optional

_logger = logging.getLogger(__name__)
_LOCK = threading.Lock()
_RING: deque[dict] = deque(maxlen=5000)
_SEQ = 0


def log(tipo: str, origem: str = "motor", utilizador: Optional[str] = None,
        seccao: Optional[str] = None, antes: Optional[dict] = None,
        depois: Optional[dict] = None, justificacao: str = "") -> dict:
    """Regista uma decisão/comando. Devolve a entrada criada."""
    global _SEQ
    with _LOCK:
        _SEQ += 1
        entry = {
            "id": _SEQ,
            "ts_ms": int(time.time() * 1000),
            "tipo": str(tipo),
            "origem": str(origem),
            "utilizador": utilizador,
            "seccao": seccao,
            "antes": antes,
            "depois": depois,
            "justificacao": justificacao or "",
        }
        _RING.append(entry)
    _persist_async(entry)
    return dict(entry)


def query(tipo: Optional[str] = None, seccao: Optional[str] = None,
          limit: int = 100) -> list[dict]:
    with _LOCK:
        items = list(_RING)
    if tipo:
        items = [e for e in items if e["tipo"] == tipo]
    if seccao:
        items = [e for e in items if e["seccao"] == seccao]
    return list(reversed(items))[: max(1, min(int(limit), 1000))]


def reset() -> None:
    global _SEQ
    with _LOCK:
        _RING.clear()
        _SEQ = 0


def _persist_async(entry: dict) -> None:
    """Persistência best-effort sem bloquear o caminho da decisão."""
    try:
        import asyncio
        from app.db import AsyncSessionLocal
        if AsyncSessionLocal is None:
            return
        loop = asyncio.get_running_loop()
        loop.create_task(_persist(AsyncSessionLocal, entry))
    except Exception:
        pass  # sem loop (testes síncronos) ou sem BD — o anel guarda na mesma


async def _persist(session_factory, entry: dict) -> None:
    try:
        from app.models.db.operations import DecisionLog
        async with session_factory() as session:
            session.add(DecisionLog(
                ts_ms=entry["ts_ms"], tipo=entry["tipo"], origem=entry["origem"],
                utilizador=entry["utilizador"], seccao=entry["seccao"],
                antes=entry["antes"], depois=entry["depois"],
                justificacao=entry["justificacao"],
            ))
            await session.commit()
    except Exception as exc:
        _logger.debug("decision_log persist erro (ignorado): %s", exc)
