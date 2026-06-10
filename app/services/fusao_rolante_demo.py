"""
PlantaOS — Orquestrador de demonstração da fusão rolante.

Em modo SIMULAÇÃO (fleet mode = "sim"), alimenta os estimadores da fusão
rolante com movimento sintético coerente com as curvas do festival
(fleet_sim): WiFi por bandas a cada tick + contagens de cabeças periódicas.
A regressão aprende ao vivo, a trava física dispara em picos orquestrados,
a calibração por nó tem efeito imediato visível.

HONESTIDADE TOTAL:
  - tudo o que entra por aqui leva origem="simulado" (visível no payload)
  - se uma secção recebeu dados REAIS há menos de 5 min, o driver NÃO lhe toca
  - em fleet mode = "real" o driver pára por completo
  - desactivável com FUSAO_DEMO=off
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import os
import time

from app.services import fusao_rolante as fr
from app.services import fleet_sim

_logger = logging.getLogger(__name__)

TICK_S = 20.0                 # cadência do driver
HEADS_EVERY_TICKS = 6         # contagem de cabeças a cada ~2 min
SPIKE_EVERY_S = 15 * 60.0     # pico orquestrado (mostra a trava física)
REAL_GUARD_S = 300.0          # secção com dados reais há <5 min é intocável

# "verdade no terreno" por secção: declive real a_true (pessoas por mac)
# determinístico mas distinto por secção — a regressão tem algo para aprender
def _a_true(section_id: str) -> float:
    h = int(hashlib.md5(f"atrue:{section_id}".encode()).hexdigest()[:8], 16)
    base = 0.55 if fr.is_interior_fechado(section_id.split("_")[0]) else 0.45
    return round(base + 0.18 * (h / 0xFFFFFFFF), 3)


def _k_real(node_id: str) -> float:
    """Ganho físico real de cada nó (antena/posição) — o que a calibração
    por nó existe para compensar. Determinístico em [0.8, 1.3]."""
    h = int(hashlib.md5(f"kreal:{node_id}".encode()).hexdigest()[:8], 16)
    return round(0.8 + 0.5 * (h / 0xFFFFFFFF), 3)


def _noise(key: str, t: float, amp: float = 0.06) -> float:
    """Ruído determinístico ±amp, estável em buckets de 30s."""
    h = int(hashlib.md5(f"{key}:{int(t // 30)}".encode()).hexdigest()[:8], 16)
    return 1.0 + amp * (2.0 * (h / 0xFFFFFFFF) - 1.0)


def _spike_section(t: float) -> str | None:
    """A cada SPIKE_EVERY_S, escolhe uma secção para um pico de 1 tick."""
    bucket = int(t // SPIKE_EVERY_S)
    if int(t // TICK_S) % int(SPIKE_EVERY_S // TICK_S) != 1:
        return None
    secs = [s["section_id"] for s in fr._sections_from_geo()]
    h = int(hashlib.md5(f"spike:{bucket}".encode()).hexdigest()[:8], 16)
    return secs[h % len(secs)]


def _section_truth(sec: dict, t: float) -> tuple[float, float]:
    """(pessoas_dentro, fila) verdadeiros da secção, das curvas do festival."""
    fill = fleet_sim.cluster_fill(sec["cluster_id"], t)
    pessoas = sec["capacidade"] * min(1.0, fill) * _noise(f"p:{sec['section_id']}", t, 0.05)
    fila = sec["capacidade"] * 0.6 * max(0.0, fill - 0.70) / 0.30
    fila *= _noise(f"q:{sec['section_id']}", t, 0.10)
    return max(0.0, pessoas), max(0.0, fila)


def demo_tick(now_s: float | None = None) -> int:
    """Um tick de orquestração. Devolve o nº de secções alimentadas."""
    t = now_s if now_s is not None else time.time()
    tick_n = int(t // TICK_S)
    spike_sid = _spike_section(t)
    fed = 0

    for sec in fr._sections_from_geo():
        sid = sec["section_id"]
        est = fr.get_estimador(sid)
        if est is None:
            continue
        # dados REAIS recentes mandam — o driver não toca na secção
        if (est.origem == "real" and est.tem_dados
                and est.ts_estimativa is not None
                and t - est.ts_estimativa < REAL_GUARD_S):
            continue

        pessoas, fila = _section_truth(sec, t)
        a_true = _a_true(sid)
        spike = 6.0 if sid == spike_sid else 1.0

        # WiFi por bandas, nó a nó (mediana + k por nó fazem o resto)
        for pos in sec["posicoes"]:
            node_id = f"{sid}_{pos}"
            k_real = _k_real(node_id)
            macs_a = (pessoas / max(a_true, 0.01)) * k_real * spike \
                * _noise(f"a:{node_id}", t)
            macs_b = (fila / max(a_true, 0.01)) * k_real \
                * _noise(f"b:{node_id}", t)
            fr.ingest_wifi_bandas(
                sec["cluster_id"], sec["secao"], node_id,
                int(round(macs_a)), int(round(macs_b)),
                ts_ms=int(t * 1000), origem="simulado",
                now_s=t,   # ts sintético: o "agora" da chamada é o próprio t
            )

        # contagem de cabeças periódica (âncora) — fontes alternadas
        if tick_n % HEADS_EVERY_TICKS == 0:
            fonte = "prosegur" if (tick_n // HEADS_EVERY_TICKS) % 2 == 0 else "luxonis"
            cabecas = pessoas * _noise(f"c:{sid}", t, 0.04)
            fr.ingest_cabecas(
                sec["cluster_id"], sec["secao"],
                int(round(cabecas)), fonte=fonte,
                ts_ms=int(t * 1000), origem="simulado",
                now_s=t,   # ts sintético: o "agora" da chamada é o próprio t
            )
        fed += 1
    return fed


def _demo_enabled() -> bool:
    if os.getenv("FUSAO_DEMO", "on").lower() in ("off", "0", "false"):
        return False
    try:
        from app.routers import fleet
        return fleet._MODE == "sim"
    except Exception:
        return False


async def demo_loop() -> None:
    """Loop do orquestrador: um demo_tick a cada TICK_S em modo sim."""
    await asyncio.sleep(5)   # deixa o arranque (snapshot reload) terminar
    _logger.info("fusao_rolante_demo: orquestrador iniciado (tick %.0fs)", TICK_S)
    while True:
        try:
            if _demo_enabled():
                demo_tick()
                # live payload deve reflectir o movimento novo
                try:
                    from app.services import state as _state
                    _state._PAYLOAD_CACHE["data"] = None
                except Exception:
                    pass
        except Exception as exc:
            _logger.debug("fusao_rolante_demo tick erro (ignorado): %s", exc)
        await asyncio.sleep(TICK_S)
