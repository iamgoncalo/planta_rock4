"""
PlantaOS — AMBIENTE (chuva, calor, vento, lama): efeitos CANÓNICOS, nunca implícitos.

Flags de ambiente em memória (thread-safe), accionadas pelo operador (ou
forecast). Os outros módulos consomem FUNÇÕES PURAS deste módulo:
  dwell_factor()             → 1.4 com chuva activa (S01)
  procura_factor()           → ×1.2 chuva · ×1.15 calor >30 °C (S01/S04)
  velocidade_aresta_m_min()  → ≈46.7 m/min em lama (0.8 m/s vs 1.2 m/s)

Lama POR ARESTA (S02) com ids canónicos "A|B" ordenados (ex. "WC-01|WC-08").
Lama GENERALIZADA (S03): chuva activa há >60 min ⇒ todas as arestas em lama,
reversível quando a chuva pára. Arestas "cortada" saem do grafo (S09).

Auditoria: cada mudança vai ao decision_log (origem="operador", antes/depois)
E a um EVENT_LOG próprio (anel de 2000 eventos com inicio_ts/fim_ts).
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Optional

FLAGS = ("chuva", "calor", "vento")
INTENSIDADES = ("fraca", "moderada", "forte")
ESTADOS_ARESTA = ("normal", "lama", "cortada")

DWELL_FACTOR_CHUVA = 1.4          # S01: dwell ×1.4 com chuva
PROCURA_FACTOR_CHUVA = 1.2        # S01: procura ×1.2 com chuva
PROCURA_FACTOR_CALOR = 1.15       # S04: procura ×1.15 com calor >30 °C
CALOR_LIMIAR_C = 30.0
LAMA_GENERALIZADA_S = 60 * 60.0   # S03: >60 min de chuva ⇒ lama em todo o lado
FACTOR_LAMA = 0.8 / 1.2           # 0.8 m/s em lama vs 1.2 m/s em piso normal

_LOCK = threading.RLock()


def _estado_inicial() -> dict:
    return {
        "chuva": {"activa": False, "intensidade": None, "desde_ts": None},
        "calor": {"activo": False, "temp_c": None},
        "vento": {"activo": False, "kmh": None},
        "fonte": "operador",
    }


_ESTADO: dict = _estado_inicial()

# EVENT_LOG próprio: {flag, inicio_ts, fim_ts|None, detalhe}
EVENT_LOG: deque[dict] = deque(maxlen=2000)

# aresta_id canónico -> "lama" | "cortada" (ausente = normal)
_ARESTAS: dict[str, str] = {}


def _log(tipo: str, utilizador: Optional[str], antes: dict, depois: dict,
         justificacao: str = "", seccao: Optional[str] = None) -> None:
    """Auditoria best-effort — nunca derruba o caminho do comando."""
    try:
        from app.services import decision_log
        decision_log.log(tipo=tipo, origem="operador", utilizador=utilizador,
                         seccao=seccao, antes=antes, depois=depois,
                         justificacao=justificacao)
    except Exception:
        pass


# ── Flags de ambiente ────────────────────────────────────────────────────────
def set_flag(flag: str, activo: bool, utilizador: str,
             intensidade: Optional[str] = None,
             temp_c: Optional[float] = None,
             kmh: Optional[float] = None,
             justificacao: str = "",
             fonte: str = "operador") -> dict:
    """Liga/desliga uma flag de ambiente. SEMPRE auditado (decision_log +
    EVENT_LOG). Flag desconhecida ⇒ ValueError (o router devolve 422)."""
    if flag not in FLAGS:
        raise ValueError(f"flag desconhecida: {flag!r} — usa chuva/calor/vento")
    if intensidade is not None and intensidade not in INTENSIDADES:
        raise ValueError(f"intensidade inválida: {intensidade!r}")
    now = time.time()
    with _LOCK:
        antes = dict(_ESTADO[flag])
        if flag == "chuva":
            novo = {
                "activa": bool(activo),
                "intensidade": ((intensidade or antes.get("intensidade")
                                 or "moderada") if activo else None),
                # desde_ts preserva-se se a chuva já estava activa
                "desde_ts": ((antes.get("desde_ts") if antes.get("activa")
                              else now) if activo else None),
            }
        elif flag == "calor":
            novo = {
                "activo": bool(activo),
                "temp_c": ((temp_c if temp_c is not None
                            else antes.get("temp_c")) if activo else None),
            }
        else:  # vento
            novo = {
                "activo": bool(activo),
                "kmh": ((kmh if kmh is not None
                         else antes.get("kmh")) if activo else None),
            }
        _ESTADO[flag] = novo
        _ESTADO["fonte"] = fonte
        # EVENT_LOG: ligar abre evento; desligar fecha o evento aberto
        aberto = next((e for e in reversed(EVENT_LOG)
                       if e["flag"] == flag and e["fim_ts"] is None), None)
        detalhe = {k: v for k, v in novo.items()}
        if activo:
            if aberto is None:
                EVENT_LOG.append({"flag": flag, "inicio_ts": now,
                                  "fim_ts": None, "detalhe": detalhe})
            else:
                aberto["detalhe"] = detalhe   # mudança de intensidade/valor
        elif aberto is not None:
            aberto["fim_ts"] = now            # flag off fecha o evento
    _log(f"ambiente_{flag}", utilizador, antes, dict(novo), justificacao)
    return dict(novo)


def flag_activa(flag: str) -> bool:
    with _LOCK:
        f = _ESTADO.get(flag, {})
        return bool(f.get("activa") or f.get("activo"))


def estado() -> dict:
    """Estado completo das flags + factores canónicos derivados."""
    with _LOCK:
        out = {f: dict(_ESTADO[f]) for f in FLAGS}
        out["fonte"] = _ESTADO["fonte"]
    out["dwell_factor"] = dwell_factor()
    out["procura_factor"] = procura_factor()
    out["lama_generalizada"] = lama_generalizada()
    return out


def estado_resumo() -> dict:
    """Resumo plano para o /state — nunca pode partir o payload."""
    with _LOCK:
        ch, ca, ve = _ESTADO["chuva"], _ESTADO["calor"], _ESTADO["vento"]
        fonte = _ESTADO["fonte"]
    return {
        "chuva": bool(ch["activa"]),
        "intensidade": ch["intensidade"],
        "calor": bool(ca["activo"]),
        "temp_c": ca["temp_c"],
        "vento": bool(ve["activo"]),
        "kmh": ve["kmh"],
        "fonte": fonte,
        "dwell_factor": dwell_factor(),
        "procura_factor": procura_factor(),
        "lama_generalizada": lama_generalizada(),
    }


def eventos() -> list[dict]:
    """EVENT_LOG completo (mais recente primeiro)."""
    with _LOCK:
        return [dict(e) for e in reversed(EVENT_LOG)]


# ── Efeitos canónicos (funções puras consumidas por outros módulos) ─────────
def dwell_factor() -> float:
    """S01: chuva activa ⇒ dwell ×1.4 (piso molhado, roupa, crianças)."""
    with _LOCK:
        return DWELL_FACTOR_CHUVA if _ESTADO["chuva"]["activa"] else 1.0


def procura_factor() -> float:
    """S01/S04: produto — ×1.2 com chuva · ×1.15 com calor >30 °C."""
    with _LOCK:
        f = 1.0
        if _ESTADO["chuva"]["activa"]:
            f *= PROCURA_FACTOR_CHUVA
        ca = _ESTADO["calor"]
        if ca["activo"] and float(ca["temp_c"] or 0.0) > CALOR_LIMIAR_C:
            f *= PROCURA_FACTOR_CALOR
        return round(f, 4)


# ── Lama / corte por aresta (S02 · S03 · S09) ───────────────────────────────
def aresta_id(a: str, b: str) -> str:
    """Id canónico de aresta: extremos ordenados, separados por '|'."""
    return "|".join(sorted((a.upper(), b.upper())))


def _normalizar(aresta: str) -> str:
    partes = aresta.upper().split("|")
    if len(partes) == 2:
        return aresta_id(partes[0], partes[1])
    return aresta.upper()


def arestas_validas() -> set[str]:
    """Todas as arestas do grafo de rota_leve (_ADJ + _LANDMARK_ADJ)."""
    from app.services.rota_leve import _ADJ, _LANDMARK_ADJ
    out: set[str] = set()
    for adj in (_ADJ, _LANDMARK_ADJ):
        for a, viz in adj.items():
            for b in viz:
                out.add(aresta_id(a, b))
    return out


def set_aresta_estado(aresta: str, estado_novo: str, utilizador: str,
                      justificacao: str = "") -> dict:
    """Marca uma aresta como lama/cortada/normal. Valida contra o grafo real
    de rota_leve — aresta inexistente ⇒ ValueError (422 no router)."""
    if estado_novo not in ESTADOS_ARESTA:
        raise ValueError(f"estado inválido: {estado_novo!r} — "
                         f"usa lama/cortada/normal")
    aid = _normalizar(aresta)
    if aid not in arestas_validas():
        raise ValueError(f"aresta desconhecida no grafo: {aresta!r}")
    with _LOCK:
        antes = _ARESTAS.get(aid, "normal")
        if estado_novo == "normal":
            _ARESTAS.pop(aid, None)
        else:
            _ARESTAS[aid] = estado_novo
    _log("aresta_estado", utilizador,
         {"aresta": aid, "estado": antes},
         {"aresta": aid, "estado": estado_novo},
         justificacao, seccao=aid)
    return {"aresta": aid, "estado": estado_novo}


def lama_generalizada(now_s: Optional[float] = None) -> bool:
    """S03: chuva activa há >60 min ⇒ lama em todas as arestas (reversível)."""
    t = now_s if now_s is not None else time.time()
    with _LOCK:
        ch = _ESTADO["chuva"]
        return bool(ch["activa"] and ch["desde_ts"] is not None
                    and t - float(ch["desde_ts"]) > LAMA_GENERALIZADA_S)


def arestas_em_lama(now_s: Optional[float] = None) -> set[str]:
    """Arestas efectivamente em lama: marcadas + generalizadas (S03)."""
    if lama_generalizada(now_s):
        return arestas_validas()
    with _LOCK:
        return {a for a, e in _ARESTAS.items() if e == "lama"}


def arestas_cortadas() -> set[str]:
    with _LOCK:
        return {a for a, e in _ARESTAS.items() if e == "cortada"}


def velocidade_aresta_m_min(aresta: str,
                            now_s: Optional[float] = None) -> float:
    """Velocidade na aresta: ≈46.7 m/min em lama (0.8/1.2), senão 70."""
    from app.services.rota_leve import VELOCIDADE_M_MIN
    aid = _normalizar(aresta)
    if aid in arestas_em_lama(now_s):
        return round(VELOCIDADE_M_MIN * FACTOR_LAMA, 1)
    return VELOCIDADE_M_MIN


def estado_arestas(now_s: Optional[float] = None) -> dict:
    """Estado de TODAS as arestas do grafo (declarado + lama efectiva)."""
    lama = arestas_em_lama(now_s)
    with _LOCK:
        declarados = dict(_ARESTAS)
    arestas = {}
    for aid in sorted(arestas_validas()):
        decl = declarados.get(aid, "normal")
        arestas[aid] = {
            "estado": decl,
            "lama_efectiva": decl != "cortada" and aid in lama,
        }
    return {
        "total": len(arestas),
        "lama_generalizada": lama_generalizada(now_s),
        "arestas": arestas,
    }


def reset() -> None:
    """Limpa flags, arestas e event log (testes)."""
    global _ESTADO
    with _LOCK:
        _ESTADO = _estado_inicial()
        _ARESTAS.clear()
        EVENT_LOG.clear()
