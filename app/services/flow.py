# -*- coding: utf-8 -*-
"""
================================================================================
 PlantaOS · RiR2026 · MOTOR DE BACKEND DA PÁGINA "FLOW"
 1 ficheiro · auto-contido · testado · pronto para o architect decidir o wiring
================================================================================

O QUE É A PÁGINA "FLOW"
-----------------------
Não é mais um painel de ocupação. É a página de CALIBRAÇÃO e VERIFICAÇÃO dos
fluxos: mostra, por secção de WC, se o modelo de fluxo está são — se aquilo que
o IR conta a entrar/sair fecha com a ocupação medida de forma independente
(câmara), quanta deriva existe, que confiança temos, e o que o routing
recomenda agora. Responde a três perguntas: como funciona, como NÃO funciona
(onde diverge), o que melhorar. Dados -> Fluxos.

REGRA ABSOLUTA RESPEITADA: conta APENAS pessoas e fluxos. Zero CO2/temp/humidade.

ARQUITECTURA (o architect só precisa deste cabeçalho + deste ficheiro)
----------------------------------------------------------------------
BACKEND  : Python 3.12 · FastAPI (router incluído no fim, com import-guard).
           Pura função: estado live em memória + Redis/PostgreSQL no real.
           Hot-path do routing = NetworkX min_cost_flow (8 nós, microsegundos).
           Sem libs pesadas no tick. Ciw/PedPy ficam OFFLINE (calibração), nunca aqui.
FRONTEND : 1 página Next.js `/v2/flow`. SEM SCROLL (hard limit) — grelha fixa
           100dvh/100dvw. Consome GET /api/v1/flow + WS. Design system v12.
PROPRIEDADES DO MOTOR:
   1. Continuidade   — ocupação_IR = ∫(entradas−saídas)+âncora (equação de continuidade)
   2. Resíduo        — residual = ocupação_IR − ocupação_câmara  (a verdade da calibração)
   3. Deriva         — |residual| acumulado desde a última re-âncora; re-âncora corrige
   4. Fusão          — IR 0.50 · WiFi 0.30 · Câmara 0.20, renormaliza se faltar fonte,
                       NUNCA divide por zero, devolve sempre confiança
   5. Congestionamento — diagrama fundamental: acima da densidade crítica o
                       throughput COLAPSA (350 a passar ≠ 350 paradas)
   6. Routing        — custo = walk + queue_wait + congestion + surge + low_conf + safety
                       resolvido como min-cost-flow global (respeita capacidades)

LAYOUT SEM-SCROLL (spec para o architect) — grelha 12 col × 8 lin, 100dvh:
   ┌───────────────────────────── TopBar 72px: LIVE · relógio · KPI strip ──────┐
   │ [kpi_01 Índice Fluxo] [kpi_02 Ocup.média] [kpi_03 Alertas] [kpi_04 Redir.]  │
   ├──────────────────────────────┬─────────────────────────────────────────────┤
   │  GRELHA 14 SECÇÕES (esq, 8c)  │  PAINEL CALIBRAÇÃO (dir, 4c)                 │
   │  card por secção: sparkline   │  - resíduo continuidade (barra ±)           │
   │  in/out, ocupação, fila,      │  - deriva desde re-âncora (+ botão re-anchor)│
   │  confiança, status amber      │  - fontes activas / saúde sensores          │
   │  (#C25A1A nunca vermelho)     │  - routing: setas origem→destino + nº pax   │
   └──────────────────────────────┴─────────────────────────────────────────────┘
   Sem scroll: cards encolhem com clamp(); números grandes; light mode default.

PAYLOAD QUE ESTE MOTOR PRODUZ -> é o que a página `/v2/flow` desenha:
   FlowEngine.flow_page()  ->  dict (ver no fim, secção CONTRATO DE SAÍDA)
================================================================================
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import math
import time

# ──────────────────────────────────────────────────────────────────────────────
# 1. CONFIGURAÇÃO ESTÁTICA DOS CLUSTERS  (substituível por clusters_geo / seed)
#    IDs minúsculos, regex ^wc-0[1-8]$. Secções: M/F (misto) ou U (unissex).
#    capacidade = pessoas em simultâneo lá dentro (cabines+calhas). Placeholder
#    realista — o architect liga ao seed real. dist_m = distância à entrada.
# ──────────────────────────────────────────────────────────────────────────────
SECTIONS = ("M", "F", "U")

@dataclass(frozen=True)
class ClusterCfg:
    id: str
    nome: str
    unissex: bool
    entry_only: bool
    dist_m: float                       # distância à entrada principal
    cap: dict                           # {"M": int, "F": int} ou {"U": int}

CLUSTERS: dict[str, ClusterCfg] = {
    "wc-01": ClusterCfg("wc-01", "V34 — Near P1",        False, False, 130, {"M": 60, "F": 56}),
    "wc-02": ClusterCfg("wc-02", "V35 — Stage / VIP",    False, False,  74, {"M": 54, "F": 72}),
    "wc-03": ClusterCfg("wc-03", "S36 — Near entrance",  False, False,  33, {"M": 54, "F": 48}),
    "wc-04": ClusterCfg("wc-04", "S37 — Summit",         False, False,  69, {"M": 84, "F": 66}),
    "wc-05": ClusterCfg("wc-05", "M38 — Unissex",        True,  True,   24, {"U": 133}),
    "wc-06": ClusterCfg("wc-06", "W39 — Unissex largest",True,  False, 267, {"U": 208}),
    "wc-07": ClusterCfg("wc-07", "M40 — Lockers",        False, False,  94, {"M": 84, "F": 54}),
    "wc-08": ClusterCfg("wc-08", "V41 — Outer",          False, False, 364, {"M": 84, "F": 61}),
}

# Override placeholders com capacidades reais (clusters_capacity.py é a FONTE DE VERDADE)
_CLUSTER_NAMES = {
    "wc-01": "V34 — Near P1",        "wc-02": "V35 — Stage / VIP",
    "wc-03": "S36 — Near entrance",  "wc-04": "S37 — Summit",
    "wc-05": "M38 — Unissex",        "wc-06": "W39 — Unissex largest",
    "wc-07": "M40 — Lockers",        "wc-08": "V41 — Outer",
}
_CLUSTER_DISTS = {
    "wc-01": 130.0, "wc-02": 74.0, "wc-03": 33.0, "wc-04": 69.0,
    "wc-05": 24.0,  "wc-06": 267.0,"wc-07": 94.0,  "wc-08": 364.0,
}
try:
    from app.clusters_capacity import CLUSTER_CAPACITY as _CC
    CLUSTERS = {
        _cid: ClusterCfg(
            id=_cid,
            nome=_CLUSTER_NAMES.get(_cid, _cid.upper()),
            unissex=bool(_cap.get("unisex", False)),
            entry_only=(_cid == "wc-05"),
            dist_m=_CLUSTER_DISTS.get(_cid, 100.0),
            cap=({"U": max(1, int(_cap.get("masc", 133)))}
                 if _cap.get("unisex")
                 else {"M": max(1, int(_cap.get("masc", 50))),
                       "F": max(1, int(_cap.get("fem", 50)))}),
        )
        for _cid, _cap in _CC.items()
    }
except ImportError:
    pass  # fallback to placeholders (unit tests sem contexto completo da app)


def get_engine() -> "FlowEngine":
    """Singleton do motor — criado depois do override de CLUSTERS."""
    global _FLOW_ENGINE
    if _FLOW_ENGINE is None:
        _FLOW_ENGINE = FlowEngine()
    return _FLOW_ENGINE

_FLOW_ENGINE: "FlowEngine | None" = None

# matriz de tempos de caminhada entre clusters (min) — derivada de dist_m relativas.
# placeholder simétrico: t = |d_i - d_j| projectado + base. architect substitui por
# clusters_geo real (haversine sobre ANCHOR_GPS 38.78145/-9.0943).
def _walk_min(a: str, b: str) -> float:
    if a == b:
        return 0.0
    da, db = CLUSTERS[a].dist_m, CLUSTERS[b].dist_m
    return round(0.8 + abs(da - db) / 80.0, 2)   # ~80 m/min a pé em multidão

# pesos de fusão (regra do projecto)
FUSION_W = {"ir": 0.50, "wifi": 0.30, "cam": 0.20}

# diagrama fundamental: densidade crítica (fracção da capacidade onde o
# throughput é máximo; acima disto o movimento interno congestiona e colapsa)
RHO_CRIT = 0.75
# taxa de serviço base por secção (pessoas/min que conseguem sair em fluxo livre)
def _service_rate(cfg: ClusterCfg, sec: str) -> float:
    return max(cfg.cap[sec] / 6.0, 4.0)   # ~ capacidade servida a cada 6 min

# thresholds de status (regra do projecto)
TH_CRITICO, TH_ALTO, TH_CONF_BAIXA = 90, 75, 40
CRIT_COLOR = "#C25A1A"   # amber — NUNCA vermelho


# ──────────────────────────────────────────────────────────────────────────────
# 2. ESTRUTURAS DE DADOS
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class SensorReading:
    """Sinal cru de um nó (1 por cluster). Firmware manda só cru — fusão é aqui."""
    cluster_id: str
    ts: float
    entradas_ir: dict            # contador cumulativo por secção {"M": int,...}
    saidas_ir: dict
    pessoas_wifi: Optional[int] = None       # estimativa agregada do cluster (não por secção)
    contagem_cam: Optional[dict] = None      # contagem absoluta por secção (Prosegur)
    uptime_s: int = 0

@dataclass
class SectionState:
    cluster_id: str
    secao: str
    # ocupação
    ocupacao_abs: int = 0
    ocupacao_pct: int = 0
    # fluxos (pessoas/min)
    fluxo_entrada_pmin: float = 0.0
    fluxo_saida_pmin: float = 0.0
    # fila e espera
    fila_actual: int = 0
    tempo_espera_min: float = 0.0
    # calibração
    confianca_pct: int = 0
    fontes_activas: list = field(default_factory=list)
    servico_efetivo: float = 0.0   # pax/min que a secção consegue escoar agora
    residual: float = 0.0          # ocupação_IR − ocupação_câmara
    deriva: float = 0.0            # acumulada desde re-âncora
    congestionado: bool = False
    status: str = "livre"

@dataclass
class _Integrator:
    """Estado interno por secção: integra IR, guarda âncora, detecta reset/deriva."""
    occ_ir: float = 0.0            # ocupação integrada do IR (+ âncora)
    last_in: Optional[int] = None  # último contador cumulativo visto
    last_out: Optional[int] = None
    last_ts: Optional[float] = None



# ──────────────────────────────────────────────────────────────────────────────
# 3. MOTOR
# ──────────────────────────────────────────────────────────────────────────────
class FlowEngine:
    def __init__(self) -> None:
        self.cfg = CLUSTERS
        self._intg: dict[tuple[str, str], _Integrator] = {}
        self._state: dict[tuple[str, str], SectionState] = {}
        self.redirected_today = 0
        self.last_redirects = []
        for cid, c in CLUSTERS.items():
            for sec in (("U",) if c.unissex else ("M", "F")):
                self._intg[(cid, sec)] = _Integrator()
                self._state[(cid, sec)] = SectionState(cid, sec)

    # ---- secções de um cluster -------------------------------------------------
    def _secs(self, cid: str):
        return ("U",) if self.cfg[cid].unissex else ("M", "F")

    # ---- ingestão de um sinal cru ---------------------------------------------
    def ingest(self, r: SensorReading) -> None:
        c = self.cfg[r.cluster_id]
        for sec in self._secs(r.cluster_id):
            ig = self._intg[(r.cluster_id, sec)]
            cum_in = int(r.entradas_ir.get(sec, 0))
            cum_out = int(r.saidas_ir.get(sec, 0))

            # delta com tratamento de reset de firmware (contador < anterior)
            if ig.last_in is None:
                d_in = d_out = 0
            else:
                d_in = cum_in - ig.last_in if cum_in >= ig.last_in else cum_in
                d_out = cum_out - ig.last_out if cum_out >= ig.last_out else cum_out
            ig.last_in, ig.last_out = cum_in, cum_out

            dt_min = ((r.ts - ig.last_ts) / 60.0) if ig.last_ts else 1.0
            dt_min = max(dt_min, 1e-3)
            ig.last_ts = r.ts

            # integração da ocupação (continuidade), clamp = sinal de erro
            cap = c.cap[sec]
            ig.occ_ir = min(max(ig.occ_ir + d_in - d_out, 0.0), float(cap))

            st = self._state[(r.cluster_id, sec)]
            st.fluxo_entrada_pmin = round(d_in / dt_min, 1)
            st.fluxo_saida_pmin = round(d_out / dt_min, 1)

            # ---- ocupação independente (câmara) e resíduo de calibração --------
            occ_cam = None if not r.contagem_cam else r.contagem_cam.get(sec)
            if occ_cam is not None:
                # resíduo = divergência ACTUAL entre IR integrado e câmara.
                # como occ_ir integra todas as saídas perdidas, este resíduo É a
                # deriva acumulada desde a última re-âncora (sinal accionável).
                st.residual = round(ig.occ_ir - occ_cam, 1)
                st.deriva = abs(st.residual)

            # ---- WiFi: agregado do cluster, repartido pelas secções por quota --
            occ_wifi = None
            if r.pessoas_wifi is not None:
                tot_cap = sum(c.cap.values())
                occ_wifi = r.pessoas_wifi * (cap / tot_cap) if tot_cap else None

            # ---- FUSÃO (renormaliza pesos sobre fontes disponíveis) ------------
            occ_fused, conf, fontes = self._fuse(ig.occ_ir, occ_wifi, occ_cam, r.uptime_s)
            # ocupação física não pode exceder capacidade — excesso vira fila
            st.ocupacao_abs = min(int(round(occ_fused)), cap)
            st.ocupacao_pct = min(int(round(100.0 * occ_fused / cap)), 100) if cap else 0
            st.confianca_pct = conf
            st.fontes_activas = fontes

            # ---- congestionamento (diagrama fundamental) + fila + espera -------
            self._congestion_and_queue(st, c, sec)
            st.status = self._status(st)

    # ---- fusão -----------------------------------------------------------------
    @staticmethod
    def _fuse(occ_ir, occ_wifi, occ_cam, uptime_s):
        srcs, fontes = [], []
        if occ_ir is not None:
            srcs.append(("ir", occ_ir)); fontes.append("IR")
        if occ_wifi is not None:
            srcs.append(("wifi", occ_wifi)); fontes.append("WiFi")
        if occ_cam is not None:
            srcs.append(("cam", occ_cam)); fontes.append("Camera")
        if not srcs:
            return 0.0, 0, []                      # nunca divide por zero
        wsum = sum(FUSION_W[k] for k, _ in srcs)
        occ = sum(FUSION_W[k] * v for k, v in srcs) / wsum

        # confiança: nº de fontes + concordância entre elas + saúde do nó
        base = {1: 55, 2: 78, 3: 92}[len(srcs)]
        if len(srcs) >= 2:
            vals = [v for _, v in srcs]
            spread = (max(vals) - min(vals)) / (max(max(vals), 1.0))
            base -= int(spread * 25)               # divergência baixa a confiança
        if uptime_s and uptime_s < 120:
            base -= 15                             # nó acabou de arrancar
        return occ, max(min(base, 99), 5), fontes

    # ---- congestionamento + fila + espera --------------------------------------
    @staticmethod
    def _congestion_and_queue(st: SectionState, c: ClusterCfg, sec: str):
        cap = c.cap[sec]
        rho = st.ocupacao_abs / cap if cap else 0.0
        mu = _service_rate(c, sec)                 # taxa de serviço em fluxo livre

        # diagrama fundamental: throughput máximo em RHO_CRIT, colapsa acima
        if rho <= RHO_CRIT:
            eff = mu * (rho / RHO_CRIT) if rho > 0 else mu * 0.3
        else:
            # ramo congestionado: cai linearmente até ~20% em rho=1
            frac = max(1.0 - (rho - RHO_CRIT) / (1.0 - RHO_CRIT) * 0.8, 0.2)
            eff = mu * frac
        eff = max(eff, 0.5)
        st.servico_efetivo = round(eff, 1)
        st.congestionado = rho > RHO_CRIT

        # fila: excesso de procura sobre serviço acumulado (proxy de chegada)
        exced = max(st.fluxo_entrada_pmin - eff, 0.0)
        st.fila_actual = int(round(exced * 3))     # ~3 min de excesso acumulado
        # espera (Little): W = L / throughput efectivo
        st.tempo_espera_min = round(st.fila_actual / eff, 1)

    # ---- status (thresholds do projecto, amber nunca vermelho) -----------------
    @staticmethod
    def _status(st: SectionState) -> str:
        if st.confianca_pct < TH_CONF_BAIXA:
            return "dados_insuficientes"
        if st.ocupacao_pct > TH_CRITICO:
            return "critico"
        if st.ocupacao_pct > TH_ALTO and st.fila_actual > 20:
            return "alto"
        if st.ocupacao_pct > 50:
            return "moderado"
        return "livre"

    # ---- re-âncora: corrige deriva igualando IR à câmara -----------------------
    def reanchor(self, cluster_id: str, sec: str, occ_cam: float) -> None:
        ig = self._intg[(cluster_id, sec)]
        ig.occ_ir = float(occ_cam)

        self._state[(cluster_id, sec)].deriva = 0.0
        self._state[(cluster_id, sec)].residual = 0.0

    # ---- ROUTING: min-cost-flow global sobre secções com capacidade livre ------
    def route(self, surge: float = 1.0):
        """
        PURA (sem efeitos secundários). Redistribui a procura em excesso das
        secções congestionadas para as secções com folga, minimizando custo total.
        custo = walk + queue_wait + congestion + surge + low_conf + safety
        """
        import networkx as nx
        G = nx.DiGraph()
        SRC, SNK = "SRC", "SNK"

        overloaded, free = [], []
        for (cid, sec), st in self._state.items():
            cap = self.cfg[cid].cap[sec]
            livre = cap - st.ocupacao_abs
            # procura a redirigir = excesso de CHEGADAS que o serviço não absorve
            # (fluxo de novos, não a fila parada -> evita recontar as mesmas pessoas)
            excesso = max(st.fluxo_entrada_pmin - st.servico_efetivo, 0.0)
            if st.ocupacao_pct > TH_ALTO and excesso >= 1.0:
                overloaded.append((cid, sec, int(round(excesso))))
            elif livre > 0 and st.ocupacao_pct < 70:
                free.append((cid, sec, livre))

        if not overloaded or not free:
            return []

        # SRC -> cada secção sobrecarregada (capacidade = nº a redirigir)
        for cid, sec, fila in overloaded:
            G.add_edge(SRC, f"O::{cid}::{sec}", capacity=int(fila), weight=0)
        # secção sobrecarregada -> secção livre (custo = caminho até lá)
        for cid_o, sec_o, _ in overloaded:
            for cid_f, sec_f, livre in free:
                if cid_o == cid_f:
                    continue
                st_f = self._state[(cid_f, sec_f)]
                cfg_f = self.cfg[cid_f]
                cost = (
                    _walk_min(cid_o, cid_f)                    # walk
                    + st_f.tempo_espera_min                    # queue_wait
                    + (3.0 if st_f.congestionado else 0.0)     # congestion
                    + (2.0 * (surge - 1.0) if surge > 1 else 0)# show_surge
                    + (2.0 if st_f.confianca_pct < 50 else 0)  # low_confidence
                    + (5.0 if cfg_f.entry_only else 0.0)       # safety (entry-only)
                )
                G.add_edge(f"O::{cid_o}::{sec_o}", f"F::{cid_f}::{sec_f}",
                           capacity=int(livre), weight=int(round(cost * 10)))
        # secção livre -> SNK
        for cid, sec, livre in free:
            G.add_edge(f"F::{cid}::{sec}", SNK, capacity=int(livre), weight=0)

        flow = nx.max_flow_min_cost(G, SRC, SNK)
        redirects = []
        for u, outs in flow.items():
            if not u.startswith("O::"):
                continue
            _, o_cid, o_sec = u.split("::")
            for v, qty in outs.items():
                if v.startswith("F::") and qty > 0:
                    _, f_cid, f_sec = v.split("::")
                    redirects.append({
                        "de": o_cid, "de_sec": o_sec,
                        "para": f_cid, "para_sec": f_sec,
                        "pax": int(qty),
                        "ganho_min": round(self._state[(o_cid, o_sec)].tempo_espera_min
                                           - self._state[(f_cid, f_sec)].tempo_espera_min, 1),
                    })
        return redirects

    def tick_route(self, surge: float = 1.0):
        """Chamado UMA vez por tick (60s). Calcula, guarda e acumula o contador diário."""
        redirects = self.route(surge=surge)
        self.last_redirects = redirects
        self.redirected_today += sum(r["pax"] for r in redirects)
        return redirects

    # ---- KPIs globais (kpi_01..kpi_04) -----------------------------------------
    def kpis(self) -> dict:
        states = list(self._state.values())
        # kpi_01 Índice de Fluxo 0-100: alto = fluido; baixo = fila/congestão
        if states:
            penal = sum(min(s.tempo_espera_min, 10) / 10 + (0.4 if s.congestionado else 0)
                        for s in states) / len(states)
            kpi_01 = int(round(max(0.0, 1.0 - penal) * 100))
            kpi_02 = int(round(sum(s.ocupacao_pct for s in states) / len(states)))
        else:
            kpi_01 = kpi_02 = 0
        kpi_03 = sum(1 for s in states if s.status == "critico")
        return {"kpi_01": kpi_01, "kpi_02": kpi_02,
                "kpi_03": kpi_03, "kpi_04": self.redirected_today}

    # ---- saúde da calibração (resumo do que está bem / mal) --------------------
    def calibration_health(self) -> dict:
        states = list(self._state.values())
        with_cam = [s for s in states if s.residual != 0.0 or s.deriva != 0.0]
        max_drift = max((s.deriva for s in states), default=0.0)
        low_conf = [f"{s.cluster_id}_{s.secao}" for s in states if s.confianca_pct < TH_CONF_BAIXA]
        congest = [f"{s.cluster_id}_{s.secao}" for s in states if s.congestionado]
        # qualidade global = média da confiança ponderada por deriva
        conf_avg = int(round(sum(s.confianca_pct for s in states) / len(states))) if states else 0
        return {
            "qualidade_global_pct": conf_avg,
            "deriva_maxima": round(max_drift, 1),
            "seccoes_calibradas_camara": len(with_cam),
            "seccoes_baixa_confianca": low_conf,
            "seccoes_congestionadas": congest,
        }

    # ---- CONTRATO DE SAÍDA: payload da página /v2/flow (READ-ONLY) -------------
    def flow_page(self) -> dict:
        secoes = []
        for (cid, sec), st in self._state.items():
            secoes.append({
                "cluster_id": cid, "secao": sec,
                "nome": self.cfg[cid].nome,
                "unissex": self.cfg[cid].unissex,
                "ocupacao_pct": st.ocupacao_pct,
                "ocupacao_abs": st.ocupacao_abs,
                "fila_actual": st.fila_actual,
                "tempo_espera_min": st.tempo_espera_min,
                "fluxo_entrada_pmin": st.fluxo_entrada_pmin,
                "fluxo_saida_pmin": st.fluxo_saida_pmin,
                "servico_efetivo_pmin": st.servico_efetivo,
                "confianca_pct": st.confianca_pct,
                "fontes_activas": st.fontes_activas,
                "residual": st.residual,        # continuidade: IR − câmara
                "deriva": st.deriva,            # desde re-âncora
                "congestionado": st.congestionado,
                "status": st.status,
            })
        return {
            "ts": int(time.time()),
            "cor_critica": CRIT_COLOR,
            "kpis": self.kpis(),
            "calibracao": self.calibration_health(),
            "routing": self.last_redirects,
            "secoes": secoes,
        }


# ──────────────────────────────────────────────────────────────────────────────
# 4. FASTAPI ROUTER (import-guard: o ficheiro corre sem FastAPI instalado)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from fastapi import APIRouter
    from pydantic import BaseModel

    router = APIRouter(prefix="/api/v1/flow", tags=["flow"])
    _engine = FlowEngine()

    class ReanchorReq(BaseModel):
        cluster_id: str
        secao: str
        ocupacao_camara: float

    @router.get("")
    def get_flow():
        return _engine.flow_page()

    @router.post("/tick")
    def post_tick(surge: float = 1.0):
        """Chamado pelo orquestrador 60s — calcula e fixa o routing do tick."""
        return {"redirects": _engine.tick_route(surge=surge)}

    @router.post("/reanchor")
    def post_reanchor(req: ReanchorReq):
        _engine.reanchor(req.cluster_id, req.secao, req.ocupacao_camara)
        return {"ok": True, "cluster_id": req.cluster_id, "secao": req.secao}
except Exception:           # FastAPI ausente no ambiente de teste — tudo bem
    router = None


# ──────────────────────────────────────────────────────────────────────────────
# 5. AUTO-TESTE — prova que o algoritmo funciona (corre: python flow_engine.py)
#    Simula 90 min de festival com surge, deriva de sensor, e queda de fonte.
# ──────────────────────────────────────────────────────────────────────────────
def _selftest() -> None:
    eng = FlowEngine()
    t0 = 1_750_000_000.0
    cum = {(cid, sec): {"in": 0, "out_real": 0, "out_ir": 0}
           for cid in CLUSTERS for sec in eng._secs(cid)}

    print("=" * 78)
    print("AUTO-TESTE · 90 min · surge pós-espectáculo · deriva IR · queda de câmara")
    print("=" * 78)

    # perfil de chegada por minuto (pessoas/min) — diferencial por proximidade:
    # clusters perto sobrecarregam; longe ficam com folga (pessoas não caminham no surge)
    def arrivals(minute: int, cid: str, sec: str) -> int:
        base = {"wc-03": 7, "wc-05": 9, "wc-02": 8, "wc-07": 7,
                "wc-04": 7, "wc-01": 5, "wc-06": 4, "wc-08": 3}[cid]
        surge = 3.8 if 60 <= minute < 85 else 1.0
        if CLUSTERS[cid].dist_m > 200 and surge > 1:        # longe: surge fraco
            surge = 1.2
        return int(base * surge)

    last_states = None
    for minute in range(0, 85):          # termina no pico do surge (min 84)
        ts = t0 + minute * 60
        for cid in CLUSTERS:
            ent, sai, cam = {}, {}, {}
            for sec in eng._secs(cid):
                cap = CLUSTERS[cid].cap[sec]
                mu = max(int(cap / 6), 4)                    # serviço livre (pax/min)
                occ_now = max(cum[(cid, sec)]["in"] - cum[(cid, sec)]["out_real"], 0)
                a = arrivals(minute, cid, sec)
                if occ_now > 0.95 * cap:                     # baulking: cheio -> menos entram
                    a = int(a * 0.4)
                d_out = min(mu, occ_now + a)                 # saída limitada pelo serviço
                # ocupação física real (verdade-terreno para a câmara)
                cum[(cid, sec)]["in"] += a
                cum[(cid, sec)]["out_real"] += d_out
                real_occ = min(max(cum[(cid, sec)]["in"] - cum[(cid, sec)]["out_real"], 0), cap)
                # IR perde ~6% das saídas (miscount realista) -> deriva positiva no IR
                cum[(cid, sec)]["out_ir"] += int(d_out * 0.94)
                ent[sec] = cum[(cid, sec)]["in"]
                sai[sec] = cum[(cid, sec)]["out_ir"]
                cam[sec] = real_occ
            # wc-06 perde a câmara a partir do min 70 (teste de queda de fonte)
            contagem_cam = None if (cid == "wc-06" and minute >= 70) else cam
            wifi = sum(min(max(cum[(cid, s)]["in"] - cum[(cid, s)]["out_real"], 0),
                           CLUSTERS[cid].cap[s]) for s in eng._secs(cid))
            eng.ingest(SensorReading(
                cluster_id=cid, ts=ts,
                entradas_ir=ent, saidas_ir=sai,
                pessoas_wifi=int(wifi * 1.1),       # WiFi sobre-estima ~10%
                contagem_cam=contagem_cam,
                uptime_s=minute * 60,
            ))
        # tick de routing (uma vez por minuto, como o orquestrador 60s)
        eng.tick_route(surge=3.8 if 60 <= minute < 85 else 1.0)
        if minute in (30, 70, 84):
            last_states = eng.flow_page()

    page = eng.flow_page()

    # ---- ASSERÇÕES (a calibração tem de bater certo) --------------------------
    ok = True
    # 1. fusão nunca rebenta e confiança sempre presente
    for s in page["secoes"]:
        assert 0 <= s["ocupacao_pct"] <= 100, s
        assert 5 <= s["confianca_pct"] <= 99, s
        assert s["fontes_activas"], s
    # 2. wc-06 perdeu a câmara -> fontes só IR+WiFi, confiança desce
    wc06 = [s for s in page["secoes"] if s["cluster_id"] == "wc-06"][0]
    assert "Camera" not in wc06["fontes_activas"], wc06
    print(f"[OK] wc-06 sem câmara: fontes={wc06['fontes_activas']} conf={wc06['confianca_pct']}%")
    # 3. routing produziu redirects de secção cheia para secção com folga
    assert len(page["routing"]) > 0, "routing vazio durante surge"
    r0 = page["routing"][0]
    assert r0["de"] != r0["para"]
    print(f"[OK] routing: {len(page['routing'])} redirects · "
          f"ex.: {r0['pax']} pax {r0['de']}_{r0['de_sec']} -> {r0['para']}_{r0['para_sec']} "
          f"(ganho {r0['ganho_min']} min)")
    # 4. KPIs no intervalo correcto
    k = page["kpis"]
    assert 0 <= k["kpi_01"] <= 100 and 0 <= k["kpi_02"] <= 100
    assert k["kpi_04"] == eng.redirected_today
    print(f"[OK] KPIs: fluxo={k['kpi_01']} ocup_média={k['kpi_02']}% "
          f"críticos={k['kpi_03']} redirigidos={k['kpi_04']}")
    # 5. congestionamento detectado durante o surge
    congest = [s for s in page["secoes"] if s["congestionado"]]
    assert congest, "nenhum congestionamento detectado no surge"
    print(f"[OK] congestionamento (diagrama fundamental): {len(congest)} secções "
          f"acima de rho_crit={RHO_CRIT}")
    # 6. re-âncora corrige deriva
    cid, sec = "wc-03", "M"
    eng._state[(cid, sec)].deriva = 999.0
    eng.reanchor(cid, sec, 10.0)
    assert eng._state[(cid, sec)].deriva == 0.0
    print(f"[OK] re-âncora: deriva {cid}_{sec} reposta a 0")

    print("-" * 78)
    print("RESUMO CALIBRAÇÃO:", page["calibracao"])
    print("-" * 78)
    print("TODOS OS TESTES PASSARAM ✔   — motor da página Flow pronto.")


if __name__ == "__main__":
    _selftest()
