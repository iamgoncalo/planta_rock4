"""
PlantaOS — Calibração por nó WiFi (fusão rolante).

Cada nó tem um factor k (default 1.0) que normaliza a sua contagem por banda:
  wifi_seccao = MEDIANA(nó_i / k_i) sobre os nós online.
Também guarda rssi_1m e threshold_dbm (banda ZONA_A acima do threshold do nó;
ZONA_B entre -70 dBm e o threshold; descartado abaixo de -70 dBm).

Estado em memória (seed k=1.0 para todos os nós da topologia) + persistência
Postgres best-effort na tabela node_calibration (mesmo padrão do ingest_store:
erros de BD nunca derrubam o serviço).
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

_logger = logging.getLogger(__name__)
_LOCK = threading.Lock()

K_DEFAULT = 1.0
THRESHOLD_DBM_DEFAULT = -60.0   # limiar ZONA_A por omissão
RSSI_1M_DEFAULT = -45.0

# node_id -> {node_id, cluster_id, secao, k, rssi_1m, threshold_dbm, actualizado_em}
_CAL: dict[str, dict] = {}
_SEEDED = False


def _seed_if_needed() -> None:
    """Seed k=1.0 para todos os nós WiFi da topologia (clusters_geo)."""
    global _SEEDED
    if _SEEDED:
        return
    try:
        from app.services.fusao_rolante import all_wifi_nodes
        now = time.time()
        for node in all_wifi_nodes():
            _CAL.setdefault(node["node_id"], {
                "node_id": node["node_id"],
                "cluster_id": node["cluster_id"],
                "secao": node["secao"],
                "k": K_DEFAULT,
                "rssi_1m": RSSI_1M_DEFAULT,
                "threshold_dbm": THRESHOLD_DBM_DEFAULT,
                "actualizado_em": now,
            })
        _SEEDED = True
    except Exception as exc:
        _logger.debug("node_calibration seed erro (ignorado): %s", exc)


def get_k(node_id: str) -> float:
    """Factor k do nó (default 1.0). Nunca devolve <= 0."""
    with _LOCK:
        _seed_if_needed()
        rec = _CAL.get(str(node_id))
        k = float(rec["k"]) if rec else K_DEFAULT
    return k if k > 0 else K_DEFAULT


def get_all() -> list[dict]:
    with _LOCK:
        _seed_if_needed()
        return [dict(rec) for rec in sorted(_CAL.values(),
                                            key=lambda r: r["node_id"])]


def get_node(node_id: str) -> Optional[dict]:
    with _LOCK:
        _seed_if_needed()
        rec = _CAL.get(str(node_id))
        return dict(rec) if rec else None


def update_node(node_id: str, *, k: Optional[float] = None,
                rssi_1m: Optional[float] = None,
                threshold_dbm: Optional[float] = None) -> Optional[dict]:
    """Actualiza a calibração de um nó existente. None se o nó não existir."""
    with _LOCK:
        _seed_if_needed()
        rec = _CAL.get(str(node_id))
        if rec is None:
            return None
        if k is not None:
            rec["k"] = float(k)
        if rssi_1m is not None:
            rec["rssi_1m"] = float(rssi_1m)
        if threshold_dbm is not None:
            rec["threshold_dbm"] = float(threshold_dbm)
        rec["actualizado_em"] = time.time()
        return dict(rec)


def reset() -> None:
    """Limpa o estado (usado em testes)."""
    global _SEEDED
    with _LOCK:
        _CAL.clear()
        _SEEDED = False


# ── Persistência Postgres (best-effort, mesmo padrão do ingest_store) ───────
async def persist_node(session_factory, node_id: str) -> None:
    """Upsert de um nó na tabela node_calibration. Silencia erros."""
    try:
        from app.models.db.operations import NodeCalibration

        rec = get_node(node_id)
        if rec is None or session_factory is None:
            return
        async with session_factory() as session:
            existing = await session.get(NodeCalibration, node_id)
            if existing:
                existing.k = rec["k"]
                existing.rssi_1m = rec["rssi_1m"]
                existing.threshold_dbm = rec["threshold_dbm"]
            else:
                session.add(NodeCalibration(
                    node_id=rec["node_id"],
                    cluster_id=rec["cluster_id"],
                    secao=rec["secao"],
                    k=rec["k"],
                    rssi_1m=rec["rssi_1m"],
                    threshold_dbm=rec["threshold_dbm"],
                ))
            await session.commit()
    except Exception as exc:
        _logger.debug("node_calibration persist erro (ignorado): %s", exc)


async def load_from_db(session_factory) -> None:
    """Ao iniciar, sobrepõe a memória com o que estiver na BD."""
    try:
        from sqlalchemy import select as _select
        from app.models.db.operations import NodeCalibration

        if session_factory is None:
            return
        async with session_factory() as session:
            result = await session.execute(_select(NodeCalibration))
            rows = result.scalars().all()
        with _LOCK:
            _seed_if_needed()
            for row in rows:
                if row.node_id in _CAL:
                    _CAL[row.node_id].update({
                        "k": float(row.k or K_DEFAULT),
                        "rssi_1m": float(row.rssi_1m or RSSI_1M_DEFAULT),
                        "threshold_dbm": float(row.threshold_dbm or THRESHOLD_DBM_DEFAULT),
                    })
        if rows:
            _logger.info("node_calibration: %d nós recarregados da BD", len(rows))
    except Exception as exc:
        _logger.debug("node_calibration load erro (ignorado): %s", exc)
