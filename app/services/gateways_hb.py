"""
PlantaOS — Heartbeat dos 2 gateways LoRaWAN (norte e sul).

Gateways canónicos: "ug65-primario" e "lg308n-reserva".
POST /api/v1/gateways/{gw_id}/heartbeat actualiza o último sinal de vida.
Um gateway calado >120 s é marcado OFFLINE; na TRANSIÇÃO online→offline
regista-se decision_log tipo="alerta_crit" ("gateway calado >2 min —
reserva assume"). Tudo em memória, single-process, com lock.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

GATEWAYS = ("ug65-primario", "lg308n-reserva")
OFFLINE_S = 120.0          # calado >2 min → offline

_LOCK = threading.Lock()
# gw_id -> {"ultimo_hb_ts": Optional[float], "online": bool}
_HB: dict[str, dict] = {}


def _init_locked() -> None:
    for gw in GATEWAYS:
        if gw not in _HB:
            _HB[gw] = {"ultimo_hb_ts": None, "online": False}


def is_known(gw_id: str) -> bool:
    return gw_id.lower() in GATEWAYS


def heartbeat(gw_id: str, now_s: Optional[float] = None) -> dict:
    """Regista um heartbeat. Lança ValueError se o gateway é desconhecido."""
    gw = gw_id.lower()
    if gw not in GATEWAYS:
        raise ValueError(f"gateway desconhecido: {gw_id}")
    t = now_s if now_s is not None else time.time()
    with _LOCK:
        _init_locked()
        _HB[gw]["ultimo_hb_ts"] = float(t)
        _HB[gw]["online"] = True
        return {"gw_id": gw, **{k: v for k, v in _HB[gw].items()}}


def estado(now_s: Optional[float] = None) -> dict[str, dict]:
    """Estado dos dois gateways. Marca offline se calado >120 s e na
    TRANSIÇÃO online→offline regista alerta_crit no decision_log."""
    t = now_s if now_s is not None else time.time()
    transitaram: list[str] = []
    with _LOCK:
        _init_locked()
        out: dict[str, dict] = {}
        for gw, rec in _HB.items():
            ts = rec["ultimo_hb_ts"]
            online = ts is not None and (t - ts) <= OFFLINE_S
            if rec["online"] and not online:
                transitaram.append(gw)
            rec["online"] = online
            out[gw] = {
                "ultimo_hb_ts": ts,
                "online": online,
                "idade_s": round(max(0.0, t - ts), 1) if ts is not None else None,
            }
    for gw in transitaram:
        try:
            from app.services import decision_log
            decision_log.log(
                tipo="alerta_crit", origem="motor", seccao=gw,
                antes={"online": True}, depois={"online": False},
                justificacao="gateway calado >2 min — reserva assume",
            )
        except Exception:
            pass
    return out


def reset() -> None:
    """Limpa o estado (testes)."""
    with _LOCK:
        _HB.clear()
