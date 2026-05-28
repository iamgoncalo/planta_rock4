"""
PlantaOS — Store em memoria do ultimo payload REAL por cluster.
Thread-safe (lock). TTL: se nao chega dado ha > ttl_s, fica STALE.
Nao persiste (reinicia a vazio). Para historico, ver Fase futura.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

_LOCK = threading.Lock()
# cluster_id -> {"params": {...}, "ts_server": float, "ts_device": int}
_STORE: dict[str, dict] = {}


def put(cluster_id: str, params: dict, ts_device: Optional[int] = None) -> None:
    cid = cluster_id.lower()
    with _LOCK:
        _STORE[cid] = {
            "params": dict(params),
            "ts_server": time.time(),
            "ts_device": int(ts_device) if ts_device else int(time.time() * 1000),
        }


def get(cluster_id: str) -> Optional[dict]:
    cid = cluster_id.lower()
    with _LOCK:
        rec = _STORE.get(cid)
        return dict(rec) if rec else None


def age_s(cluster_id: str) -> Optional[float]:
    """Segundos desde o ultimo dado real. None se nunca houve."""
    rec = get(cluster_id)
    if not rec:
        return None
    return time.time() - rec["ts_server"]


def freshness(cluster_id: str, ttl_s: float) -> str:
    """'real' se recente, 'stale' se expirou, 'none' se nunca houve."""
    a = age_s(cluster_id)
    if a is None:
        return "none"
    return "real" if a <= ttl_s else "stale"


def snapshot(ttl_s: float) -> dict:
    """Estado de todos os clusters: fonte + idade. Para observabilidade."""
    with _LOCK:
        out = {}
        now = time.time()
        for cid, rec in _STORE.items():
            a = now - rec["ts_server"]
            out[cid] = {
                "data_source": "real" if a <= ttl_s else "stale",
                "age_s": round(a, 1),
                "ts_device": rec["ts_device"],
            }
        return out
