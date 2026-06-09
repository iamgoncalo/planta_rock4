"""
PlantaOS — Estado e regras POR SECÇÃO (onda 6 · mulheres primeiro).

14 secções: 6 clusters M/F (WC-0X_M, WC-0X_F) + 2 unissexo (WC-05, WC-06).
  servico (pessoas/min) = posicoes_seccao / dwell
  dwell: M=2.0 min · F=3.6 min · unissexo=2.8 min  (calibráveis no terreno)
  espera_prevista_min  = fila / servico
  queue_cap por secção = ESPERA_cluster × posicoes_seccao / posicoes_totais
ESPERA por cluster vem EXCLUSIVAMENTE do seed (clusters_capacity).

Encaminhamento por género: F só vê secções F + unissexo; M só M + unissexo.
REGRA WC-05 (steward): bloquear quando (interior+fila) > 0.85×(cap+espera).
Alertas de fila: WARN fila/queue_cap > 0.7 · CRIT > 0.95.
Modo de falha: cluster_fechado ⇒ servico=0, excluído do encaminhamento,
alerta CRIT e recusas_estimadas expostas. Tudo auditado no decision_log.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from app.clusters_capacity import CLUSTER_CAPACITY, ALL_CLUSTERS, is_unisex

# Dwell por tipo de secção (minutos por utilização) — calibráveis no terreno
DWELL_MIN = {"m": 2.0, "f": 3.6, "u": 2.8}

# Limiares de alerta sobre a fila (fila / queue_cap)
WARN_FILA = 0.70
CRIT_FILA = 0.95

# Regra WC-05: bloquear steward quando (interior+fila) > 0.85×(cap+espera)
WC05_BLOQUEIO = 0.85

_LOCK = threading.Lock()
# cluster_id -> {"fechado": bool, "por": str, "ts_ms": int, "justificacao": str}
_FECHADOS: dict[str, dict] = {}


def section_ids() -> list[str]:
    out = []
    for cid in ALL_CLUSTERS:
        if is_unisex(cid):
            out.append(cid)
        else:
            out.extend([f"{cid}_m", f"{cid}_f"])
    return out


def _split(section_id: str) -> tuple[str, str]:
    sid = section_id.lower()
    if "_" in sid:
        cid, sec = sid.split("_", 1)
        return cid, sec
    return sid, "u"


def posicoes(section_id: str) -> int:
    """Lugares simultâneos da secção (do seed)."""
    cid, sec = _split(section_id)
    cap = CLUSTER_CAPACITY.get(cid, {})
    if sec == "f":
        return max(1, int(cap.get("fem", 1)))
    return max(1, int(cap.get("masc", 1)))   # m e unissexo (masc guarda o total)


def queue_cap(section_id: str) -> float:
    """Capacidade da zona de espera da secção = ESPERA × quota de posições."""
    cid, sec = _split(section_id)
    cap = CLUSTER_CAPACITY.get(cid, {})
    espera = float(cap.get("espera", 0.0))
    total = max(1, int(cap.get("masc", 0)) + int(cap.get("fem", 0)))
    return round(espera * posicoes(section_id) / total, 1)


def servico_pmin(section_id: str) -> float:
    """Débito da secção (pessoas/min). 0 se o cluster estiver fechado."""
    cid, sec = _split(section_id)
    if is_fechado(cid):
        return 0.0
    dwell = DWELL_MIN.get(sec, DWELL_MIN["u"])
    return posicoes(section_id) / max(dwell, 0.001)


def espera_prevista_min(section_id: str, fila: float) -> float:
    """espera = fila/serviço. Fechado ⇒ infinito operacional (999)."""
    s = servico_pmin(section_id)
    if s <= 0:
        return 999.0
    return round(max(0.0, float(fila)) / max(s, 0.001), 1)


def alerta_fila(section_id: str, fila: float) -> Optional[str]:
    """WARN >0.7 · CRIT >0.95 da queue_cap. CRIT imediato se fechado."""
    cid, _ = _split(section_id)
    if is_fechado(cid):
        return "CRIT"
    qc = max(queue_cap(section_id), 0.001)
    r = max(0.0, float(fila)) / qc
    if r > CRIT_FILA:
        return "CRIT"
    if r > WARN_FILA:
        return "WARN"
    return None


def wc05_bloquear_steward(interior: float, fila: float) -> bool:
    """REGRA WC-05: (interior+fila) > 0.85×(cap+espera) — NUNCA só interior."""
    cap = CLUSTER_CAPACITY.get("wc-05", {})
    limite = WC05_BLOQUEIO * (float(cap.get("masc", 0)) + float(cap.get("espera", 0)))
    return (max(0.0, interior) + max(0.0, fila)) > limite


def seccoes_permitidas(genero: str) -> list[str]:
    """F vê F+unissexo · M vê M+unissexo. NUNCA cruzar."""
    g = (genero or "").strip().lower()[:1]
    out = []
    for sid in section_ids():
        cid, sec = _split(sid)
        if is_fechado(cid):
            continue
        if sec == "u" or (g == "f" and sec == "f") or (g == "m" and sec == "m"):
            out.append(sid)
    return out


# ── cluster_fechado (modo de falha, auditado) ───────────────────────────────
def is_fechado(cluster_id: str) -> bool:
    with _LOCK:
        return bool(_FECHADOS.get(cluster_id.lower(), {}).get("fechado"))


def estado_fechados() -> dict[str, dict]:
    with _LOCK:
        return {k: dict(v) for k, v in _FECHADOS.items()}


def set_fechado(cluster_id: str, fechado: bool, utilizador: str,
                justificacao: str = "") -> dict:
    """Fecha/reabre um cluster. SEMPRE auditado no decision_log."""
    cid = cluster_id.lower()
    ts_ms = int(time.time() * 1000)
    with _LOCK:
        antes = dict(_FECHADOS.get(cid, {"fechado": False}))
        rec = {"fechado": bool(fechado), "por": utilizador,
               "ts_ms": ts_ms, "justificacao": justificacao}
        _FECHADOS[cid] = rec
    try:
        from app.services import decision_log
        decision_log.log(
            tipo="cluster_fechado" if fechado else "cluster_reaberto",
            origem="operador", utilizador=utilizador, seccao=cid,
            antes=antes, depois=dict(rec), justificacao=justificacao,
        )
    except Exception:
        pass
    return dict(rec)


def recusas_estimadas() -> dict:
    """Pessoas sem fila disponível: excesso sobre queue_cap nas secções abertas
    + fila inteira das fechadas. Por género e total."""
    try:
        from app.services import fusao_rolante
        todos = fusao_rolante.get_all()
    except Exception:
        todos = {}
    out = {"m": 0.0, "f": 0.0, "u": 0.0, "total": 0.0}
    for sid in section_ids():
        p = todos.get(sid)
        if p is None:
            continue
        cid, sec = _split(sid)
        fila = float(p.get("fila_estimada") or 0.0)
        if is_fechado(cid):
            exc = fila
        else:
            exc = max(0.0, fila - queue_cap(sid))
        out[sec] = round(out[sec] + exc, 1)
    out["total"] = round(out["m"] + out["f"] + out["u"], 1)
    return out


def reset() -> None:
    """Limpa fechados (testes)."""
    with _LOCK:
        _FECHADOS.clear()
