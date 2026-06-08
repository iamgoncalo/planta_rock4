"""
PlantaOS — Store em memoria do ultimo payload REAL por cluster.
Thread-safe (lock). TTL: se nao chega dado ha > ttl_s, fica STALE.
Nao persiste (reinicia a vazio). Para historico, ver flow_history.

v2: acumulacao por porta para clusters M/F (LLH/LRH/LLW/LRW).
Dois LilyGo do mesmo cluster sao SOMADOS, nao sobrescritos.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

_LOCK = threading.Lock()

# cluster_id -> {"params": {...}, "ts_server": float, "ts_device": int}
_STORE: dict[str, dict] = {}

# cluster_id -> porta_key -> {"params", "ts_server", "ts_device", "secao"}
# porta_key ex: "LL_m", "LR_f", "C_m"
_PORTA_STORE: dict[str, dict[str, dict]] = {}
_PORTA_TTL_S: float = 300.0  # porta considerada stale apos 5 min sem update


def put(cluster_id: str, params: dict, ts_device: Optional[int] = None,
        porta: Optional[str] = None, secao: Optional[str] = None) -> None:
    """
    Guarda payload de ingest.

    Se porta+secao presentes (LilyGo M/F com IR):
      — actualiza _PORTA_STORE e reconstroi agregado _STORE (soma IR de todas portas).
    Caso contrario (LC/center, Luxonis, Prosegur, payload sem porta):
      — actualiza _STORE sem destruir o IR ja acumulado pelas portas activas.
    """
    cid = cluster_id.lower()
    now = time.time()
    ts_dev = int(ts_device) if ts_device else int(now * 1000)

    with _LOCK:
        if porta and secao:
            pk = f"{porta.upper()}_{secao.lower()}"
            if cid not in _PORTA_STORE:
                _PORTA_STORE[cid] = {}
            _PORTA_STORE[cid][pk] = {
                "params":    dict(params),
                "ts_server": now,
                "ts_device": ts_dev,
                "secao":     secao.lower(),
            }
            _rebuild_agg(cid, now, ts_dev)
        else:
            # Nao-IR (LC, Luxonis, Prosegur): merge sem tocar no IR acumulado
            existing_params = _STORE.get(cid, {}).get("params", {})
            merged = dict(existing_params)
            ir_agg_keys = {
                "entradas_ir", "saidas_ir",
                "entradas_ir_m", "saidas_ir_m",
                "entradas_ir_f", "saidas_ir_f",
                "portas_ativas",
            }
            has_active_portas = any(
                now - rec["ts_server"] < _PORTA_TTL_S
                for rec in _PORTA_STORE.get(cid, {}).values()
            )
            for k, v in params.items():
                # Nunca sobrescreve IR calculado a partir de portas activas
                if k in ir_agg_keys and has_active_portas:
                    continue
                merged[k] = v
            _STORE[cid] = {
                "params":    merged,
                "ts_server": now,
                "ts_device": ts_dev,
            }


def _rebuild_agg(cid: str, now: float, latest_ts_dev: int) -> None:
    """Reconstroi _STORE[cid] somando IR de todas as portas activas. Requer _LOCK."""
    portas = _PORTA_STORE.get(cid, {})
    active = {pk: rec for pk, rec in portas.items()
              if now - rec["ts_server"] < _PORTA_TTL_S}
    if not active:
        return

    ir: dict[str, dict[str, int | float]] = {
        "m": {"in": 0, "out": 0, "pax": 0.0},
        "f": {"in": 0, "out": 0, "pax": 0.0},
    }
    has_sec: dict[str, bool] = {"m": False, "f": False}
    latest_ts = 0.0

    for pk, rec in active.items():
        sec = rec["secao"]  # "m" ou "f"
        p = rec["params"]
        if sec in ir:
            ir[sec]["in"]  += int(p.get("entradas_ir") or 0)
            ir[sec]["out"] += int(p.get("saidas_ir")   or 0)
            ir[sec]["pax"] += float(p.get("pessoas_estimadas") or 0)
            has_sec[sec] = True
        if rec["ts_server"] > latest_ts:
            latest_ts = rec["ts_server"]

    # Merge com campos nao-IR existentes (prosegur, estado_sensor, luxonis, etc.)
    existing_params = _STORE.get(cid, {}).get("params", {})
    merged = dict(existing_params)
    merged.update({
        "entradas_ir":   ir["m"]["in"]  + ir["f"]["in"],
        "saidas_ir":     ir["m"]["out"] + ir["f"]["out"],
        "entradas_ir_m": ir["m"]["in"],
        "saidas_ir_m":   ir["m"]["out"],
        "entradas_ir_f": ir["f"]["in"],
        "saidas_ir_f":   ir["f"]["out"],
        "portas_ativas": list(active.keys()),
    })
    if has_sec["m"]:
        merged["homens"] = int(ir["m"]["pax"])
    if has_sec["f"]:
        merged["mulheres"] = int(ir["f"]["pax"])

    _STORE[cid] = {
        "params":    merged,
        "ts_server": latest_ts or now,
        "ts_device": latest_ts_dev,
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
    """Estado de todos os clusters: fonte + idade + portas activas."""
    with _LOCK:
        out = {}
        now = time.time()
        for cid, rec in _STORE.items():
            a = now - rec["ts_server"]
            portas = list(rec["params"].get("portas_ativas") or [])
            out[cid] = {
                "data_source":   "real" if a <= ttl_s else "stale",
                "age_s":         round(a, 1),
                "ts_device":     rec["ts_device"],
                "portas_ativas": portas,
            }
        return out
