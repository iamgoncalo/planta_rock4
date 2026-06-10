"""
PlantaOS — Fusão rolante CABEÇAS + WIFI (regressão rolante por secção).

Sem IR completo no terreno, a ocupação por secção vem de:
  - CONTADOR DE CABEÇAS  → âncora absoluta, periódica (Prosegur/Luxonis/manual)
  - WIFI LilyGo por bandas RSSI → tendência rápida (cada 60s, por nó)

Modelo por secção:
  ocupacao = c_ultima + a * (wifi_agora − wifi_no_instante_de_c_ultima)
  a — declive da regressão rolante (w, c), janela 36 pares OU 3 horas
      fit só se var(w) >= 0.5, clamp a ∈ [0.3, 4.0]
  trava física: |delta/min| <= n_acessos × 40 (×3.8 em surto pós-show 25 min)
  0 nós online → fonte offline, decaimento exponencial (tau 20 min)
  fila_estimada = a × macs_zona_B (mediana entre nós), mesmo clamp

confianca_cruzada = (0.45·c1 + 0.35·c2 + 0.20·c3) / max(Σ pesos disponíveis, ε)
  c1 = exp(−idade_ultima_cabeca_min / 15) · c2 = R² da regressão ·
  c3 = nós_online / nós_totais

Invariantes:
  - capacidade_seccao e n_acessos lidos de clusters_geo.py / seed (nunca hardcoded)
  - mediana entre nós, nunca média
  - todos os divisores protegidos com max(x, ε) — nunca NaN/inf
  - apenas CONTAGENS agregadas por banda — nunca MACs individuais
  - WC-05 / WC-06 são UNISSEXO: UMA secção, sem split M/F
Estado em memória + snapshot Postgres 60s (mesmo padrão do ingest_store).
"""
from __future__ import annotations

import asyncio
import logging
import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from statistics import median
from typing import Optional

from app.clusters_geo import CLUSTERS_GEO

_logger = logging.getLogger(__name__)
_LOCK = threading.Lock()

_EPS = 0.001

# ── Parâmetros canónicos do modelo ──────────────────────────────────────────
JANELA_PARES = 36                 # nº máximo de pares (w, c) na regressão
JANELA_HORAS_S = 3 * 3600.0       # OU 3 horas
VAR_MIN = 0.5                     # guarda: fit só se var(w) >= 0.5
A_MIN, A_MAX = 0.3, 4.0           # clamp do declive
A0_EXTERIOR = 0.45                # valor inicial de a — clusters exteriores
A0_INTERIOR = 0.55                # WC-05 / WC-06 (interior fechado)
TRAVA_POR_ACESSO_PMIN = 40.0      # pessoas/min por acesso físico
SURTO_FACTOR = 3.8                # multiplicador na janela de surto pós-show
SURTO_JANELA_S = 25 * 60.0        # 25 min após o fim de um show
NO_TTL_S = 180.0                  # nó sem POST há 3 min sai do cálculo
DECAY_TAU_S = 20 * 60.0           # tau do decaimento sem nós (20 min)
PESO_C1, PESO_C2, PESO_C3 = 0.45, 0.35, 0.20
HISTORIA_MAX = 720                # pontos de memória por secção (~12h a 1/min)
HISTORIA_SNAPSHOT = 240           # pontos persistidos no snapshot Postgres

# Congestão "parada vs a fluir" (multidão parada ≠ fila a fluir)
CONGESTAO_OCUP_RATIO = 0.75       # ocupação > 0.75×capacidade…
CONGESTAO_PONTOS_MIN = 5          # …em ≥5 pontos de história…
CONGESTAO_DELTA_MAX = 1.0         # …com |delta ocupação| médio < 1.0/ponto

# Guarda de transição da flag de congestão (section_id -> última flag)
_CONGESTAO_PREV: dict[str, bool] = {}

# QUARENTENA DE NÓ (S24 — sensor a mentir)
QUARENTENA_Z = 3.0                      # |z| robusto acima do qual a leitura desvia
QUARENTENA_PERSISTENCIA_S = 10 * 60.0   # desvio mantido >= 10 min → quarentena
MAD_ESCALA = 1.4826                     # consistência MAD → desvio robusto
QUARENTENA_MIN_NOS = 3                  # mediana/MAD robustos exigem >= 3 nós

# TS_SUSPEITO (S25 — relógio errado)
TS_SKEW_MAX_S = 300.0             # |ts - agora| > 5 min → marca, não funde

# Posições canónicas dos nós WiFi (define nós_totais por secção)
POSICOES_MF = ("porta", "meio", "fundo")   # 3 por secção M/F
POSICOES_UNI = ("porta", "fundo")          # 2 por cluster unissexo


# ── Topologia derivada de clusters_geo (fonte única) ────────────────────────
def _sections_from_geo() -> list[dict]:
    """[{section_id, cluster_id, secao, capacidade, posicoes}] a partir de CLUSTERS_GEO."""
    out = []
    for c in CLUSTERS_GEO:
        cid = c["id"].lower()
        if c["type"] == "UNI":
            out.append({
                "section_id": cid, "cluster_id": cid, "secao": "u",
                "capacidade": int(c.get("cap", 0)), "posicoes": POSICOES_UNI,
            })
        else:
            out.append({
                "section_id": f"{cid}_m", "cluster_id": cid, "secao": "m",
                "capacidade": int(c.get("cap_m", 0)), "posicoes": POSICOES_MF,
            })
            out.append({
                "section_id": f"{cid}_f", "cluster_id": cid, "secao": "f",
                "capacidade": int(c.get("cap_f", 0)), "posicoes": POSICOES_MF,
            })
    return out


def _n_acessos(cluster_id: str, secao: str) -> int:
    """Nº de acessos físicos da secção, contado nos nós IR 'entry' do seed."""
    try:
        from app.seeds.sensors import SENSOR_SEED
        cid = cluster_id.lower().replace("-", "")
        prefix = f"ir_{cid}_u" if secao == "u" else f"ir_{cid}_{secao}_"
        n = sum(
            1 for node in SENSOR_SEED
            if node.get("type") == "ir"
            and str(node.get("id", "")).startswith(prefix)
            and str(node.get("id", "")).endswith("_entry")
        )
        return max(n, 1)
    except Exception:
        return 1


def is_interior_fechado(cluster_id: str) -> bool:
    """WC-05/WC-06 (UNI) são interiores fechados → a0=0.55."""
    cid = cluster_id.upper()
    for c in CLUSTERS_GEO:
        if c["id"] == cid:
            return c["type"] == "UNI"
    return False


def all_wifi_nodes() -> list[dict]:
    """Nós WiFi canónicos de toda a topologia (para seed de calibração)."""
    nodes = []
    for sec in _sections_from_geo():
        for pos in sec["posicoes"]:
            nodes.append({
                "node_id": f"{sec['section_id']}_{pos}",
                "cluster_id": sec["cluster_id"],
                "secao": sec["secao"],
            })
    return nodes


# ── Surto pós-show ───────────────────────────────────────────────────────────
def _surge_factor(now_s: float) -> float:
    """3.8 se estivermos na janela de 25 min após o fim de um show, senão 1.0."""
    try:
        from datetime import datetime
        from app.services.state import get_shows
        for show in get_shows():
            end_s = datetime.fromisoformat(show.end_iso).timestamp()
            if 0.0 <= now_s - end_s <= SURTO_JANELA_S:
                return SURTO_FACTOR
    except Exception:
        pass
    return 1.0


# ── Regressão rolante ───────────────────────────────────────────────────────
class RegressaoRolante:
    """Regressão linear rolante c ≈ a·w + b sobre pares (w, c) com janela
    de 36 pares OU 3 horas. Fit só com var(w) >= 0.5; a clamped [0.3, 4.0]."""

    def __init__(self, a0: float) -> None:
        self.a: float = a0
        self.b: float = 0.0
        self.r2: float = 0.0
        self.fitted: bool = False     # já houve pelo menos um fit válido?
        self.pares: deque[tuple[float, float, float]] = deque(maxlen=JANELA_PARES)
        # cada par: (ts_s, w, c)

    def add_pair(self, w: float, c: float, ts_s: float) -> None:
        self.pares.append((ts_s, float(w), float(c)))
        self._prune(ts_s)
        self._fit()

    def _prune(self, now_s: float) -> None:
        while self.pares and now_s - self.pares[0][0] > JANELA_HORAS_S:
            self.pares.popleft()

    def _fit(self) -> None:
        n = len(self.pares)
        if n < 2:
            return
        ws = [p[1] for p in self.pares]
        cs = [p[2] for p in self.pares]
        mw = sum(ws) / max(n, 1)
        mc = sum(cs) / max(n, 1)
        var_w = sum((w - mw) ** 2 for w in ws) / max(n, 1)
        if var_w < VAR_MIN:
            return  # guarda: mantém a/b/r2 anteriores
        cov = sum((w - mw) * (c - mc) for w, c in zip(ws, cs)) / max(n, 1)
        self.a = max(A_MIN, min(A_MAX, cov / max(var_w, _EPS)))
        self.b = mc - self.a * mw
        ss_tot = sum((c - mc) ** 2 for c in cs)
        ss_res = sum((c - (self.a * w + self.b)) ** 2 for w, c in zip(ws, cs))
        self.r2 = max(0.0, min(1.0, 1.0 - ss_res / max(ss_tot, _EPS)))
        self.fitted = True

    def to_dict(self) -> dict:
        return {"a": self.a, "b": self.b, "r2": self.r2, "fitted": self.fitted,
                "pares": [list(p) for p in self.pares]}

    @classmethod
    def from_dict(cls, d: dict, a0: float) -> "RegressaoRolante":
        r = cls(a0)
        try:
            r.a = float(d.get("a", a0))
            r.b = float(d.get("b", 0.0))
            r.r2 = float(d.get("r2", 0.0))
            r.fitted = bool(d.get("fitted", False))
            for p in d.get("pares", []):
                r.pares.append((float(p[0]), float(p[1]), float(p[2])))
        except Exception:
            pass
        return r


# ── Estimador por secção ────────────────────────────────────────────────────
@dataclass
class EstimadorSeccao:
    """Âncora (cabeças) + tendência (WiFi), trava física e decaimento."""
    section_id: str
    cluster_id: str
    secao: str                    # "m" | "f" | "u"
    capacidade: int
    n_acessos: int
    posicoes: tuple[str, ...]
    regressao: RegressaoRolante = field(default=None)  # type: ignore[assignment]

    # nó -> {"macs_A": int, "macs_B": int, "ts": float}  (contagens agregadas, NUNCA MACs)
    nos: dict[str, dict] = field(default_factory=dict)

    # âncora (última contagem de cabeças)
    c_ultima: Optional[float] = None
    ts_cabeca: Optional[float] = None
    wifi_na_ancora: Optional[float] = None
    fonte_ancora: Optional[str] = None

    # última estimativa publicada (para trava física e decaimento)
    ocupacao: Optional[float] = None
    ts_estimativa: Optional[float] = None
    fila_estimada: float = 0.0
    flag_anomalia: bool = False
    tem_dados: bool = False
    origem: str = "real"          # "simulado" quando alimentada pelo demo driver

    # MEMÓRIA — série temporal da secção (ts, ocupacao, fila, conf, a, nos, anom)
    historia: deque = field(default_factory=lambda: deque(maxlen=HISTORIA_MAX))

    # QUARENTENA (S24) — nós com leitura persistentemente fora da mediana
    quarentena: set = field(default_factory=set)
    primeiro_desvio_ts: dict = field(default_factory=dict)   # nó -> ts do 1º desvio

    # TS_SUSPEITO (S25) — última âncora chegou com relógio errado
    ancora_ts_suspeita: bool = False

    def __post_init__(self) -> None:
        if self.regressao is None:
            a0 = A0_INTERIOR if is_interior_fechado(self.cluster_id) else A0_EXTERIOR
            self.regressao = RegressaoRolante(a0)

    # — agregação entre nós (mediana, nunca média) —
    def _nos_online(self, now_s: float) -> dict[str, dict]:
        return {nid: rec for nid, rec in self.nos.items()
                if now_s - rec["ts"] <= NO_TTL_S}

    def _nos_validos(self, now_s: float) -> dict[str, dict]:
        """Nós online que PODEM fundir: fora de quarentena e com ts são."""
        return {nid: rec for nid, rec in self._nos_online(now_s).items()
                if nid not in self.quarentena and not rec.get("ts_suspeito")}

    def wifi_zona(self, now_s: float, banda: str) -> Optional[float]:
        """Mediana(nó_i / k_i) sobre os nós online válidos (sem quarentena,
        sem ts suspeito). None se 0 nós."""
        from app.services import node_calibration as _cal
        online = self._nos_validos(now_s)
        if not online:
            return None
        vals = []
        for nid, rec in online.items():
            k = _cal.get_k(nid)
            vals.append(float(rec.get(banda, 0)) / max(k, _EPS))
        return float(median(vals))

    # — quarentena de nó (S24: sensor a mentir) —
    def _verifica_quarentena(self, now_s: float) -> None:
        """Nó cuja leitura macs_A normalizada (nó/k) está persistentemente fora
        da mediana da secção (|z| > 3, desvio robusto 1.4826×MAD) durante
        >= 10 min entra em quarentena e sai da agregação wifi_zona."""
        from app.services import node_calibration as _cal
        validos = self._nos_validos(now_s)
        if len(validos) < QUARENTENA_MIN_NOS:
            return
        norm = {nid: float(rec.get("macs_A", 0)) / max(_cal.get_k(nid), _EPS)
                for nid, rec in validos.items()}
        med = float(median(norm.values()))
        mad = float(median(abs(v - med) for v in norm.values()))
        desvio = max(MAD_ESCALA * mad, _EPS)        # protegido — nunca /0
        for nid, v in norm.items():
            z = abs(v - med) / desvio
            if z <= QUARENTENA_Z:
                self.primeiro_desvio_ts.pop(nid, None)
                continue
            primeiro = self.primeiro_desvio_ts.setdefault(nid, float(now_s))
            if now_s - primeiro >= QUARENTENA_PERSISTENCIA_S:
                self.quarentena.add(nid)
                self.primeiro_desvio_ts.pop(nid, None)
                from app.services import decision_log
                decision_log.log(
                    tipo="quarentena_no", origem="motor",
                    seccao=self.section_id,
                    depois={"no": nid, "z": round(z, 2)},
                    justificacao="leitura persistentemente fora da mediana "
                                 "(z>3 por 10 min)",
                )

    # — ingestão —
    def ingest_wifi(self, no: str, macs_a: int, macs_b: int, ts_s: float,
                    origem: str = "real",
                    now_s: Optional[float] = None) -> None:
        now_s = float(now_s) if now_s is not None else time.time()
        # IDEMPOTENTE: o mesmo nó com o mesmo ts não conta duas vezes
        existente = self.nos.get(no)
        if existente is not None and existente.get("ts") == float(ts_s):
            return
        # TS_SUSPEITO (S25): relógio do nó desviado > 5 min do "agora" da
        # chamada — aceita o POST, marca o nó e NÃO funde até chegar ts são
        suspeito = abs(float(ts_s) - now_s) > TS_SKEW_MAX_S
        self.nos[no] = {"macs_A": max(0, int(macs_a)),
                        "macs_B": max(0, int(macs_b)),
                        "ts": float(ts_s),
                        "ts_suspeito": suspeito}
        if suspeito:
            return
        self.tem_dados = True
        self.origem = origem
        self._verifica_quarentena(ts_s)
        self._recompute(ts_s)
        self._memorize(ts_s)

    def ingest_cabecas(self, cabecas: float, fonte: str, ts_s: float,
                       origem: str = "real",
                       now_s: Optional[float] = None) -> None:
        now_s = float(now_s) if now_s is not None else time.time()
        cabecas = max(0.0, float(cabecas))
        # TS_SUSPEITO (S25): âncora com relógio errado é aceite mas NÃO cria
        # par (w, c) nem re-baseia a ocupação — fica só marcada no payload
        if abs(float(ts_s) - now_s) > TS_SKEW_MAX_S:
            self.ancora_ts_suspeita = True
            return
        self.ancora_ts_suspeita = False
        w = self.wifi_zona(ts_s, "macs_A")
        if w is not None:
            self.regressao.add_pair(w, cabecas, ts_s)
        self.c_ultima = cabecas
        self.ts_cabeca = float(ts_s)
        self.wifi_na_ancora = w
        self.fonte_ancora = fonte
        self.tem_dados = True
        self.origem = origem
        # âncora absoluta: re-baseia a estimativa (sem trava — é verdade no terreno)
        self.ocupacao = max(0.0, min(float(self.capacidade), cabecas))
        self.ts_estimativa = float(ts_s)
        self.flag_anomalia = False
        self._memorize(ts_s, ancora=True)

    # — memória —
    def _memorize(self, ts_s: float, ancora: bool = False) -> None:
        """Grava um ponto na série temporal da secção."""
        self.historia.append({
            "ts": round(float(ts_s), 1),
            "ocupacao": round(self.ocupacao, 1) if self.ocupacao is not None else 0.0,
            "fila": round(self.fila_estimada, 1),
            "conf": self.confianca_cruzada(ts_s),
            "a": round(self.regressao.a, 3),
            "nos": len(self._nos_online(ts_s)),
            "anomalia": bool(self.flag_anomalia),
            "ancora": bool(ancora),
        })

    # — estimativa —
    def _recompute(self, now_s: float) -> None:
        wifi_agora = self.wifi_zona(now_s, "macs_A")
        if wifi_agora is None:
            self._decay(now_s)
            return

        a = self.regressao.a
        if self.c_ultima is not None and self.wifi_na_ancora is not None:
            bruto = self.c_ultima + a * (wifi_agora - self.wifi_na_ancora)
        elif self.c_ultima is not None:
            bruto = self.c_ultima
        else:
            bruto = a * wifi_agora + self.regressao.b
        bruto = max(0.0, min(float(self.capacidade), bruto))

        # trava física: |delta/min| <= n_acessos × 40 (×3.8 em surto pós-show)
        # piso de 1 min: a cadência canónica dos nós é 60s — POSTs no mesmo
        # minuto partilham a mesma janela física, sem flags espúrias
        anomalia = False
        if self.ocupacao is not None and self.ts_estimativa is not None:
            minutos = max((now_s - self.ts_estimativa) / 60.0, 1.0)
            max_delta = self.n_acessos * TRAVA_POR_ACESSO_PMIN * _surge_factor(now_s) * minutos
            delta = bruto - self.ocupacao
            if abs(delta) > max_delta:
                bruto = self.ocupacao + math.copysign(max_delta, delta)
                bruto = max(0.0, min(float(self.capacidade), bruto))
                anomalia = True

        self.ocupacao = bruto
        self.ts_estimativa = float(now_s)
        self.flag_anomalia = anomalia

        # fila: a × mediana(macs_zona_B / k), clamp [0, queue_cap×1.5]
        zona_b = self.wifi_zona(now_s, "macs_B")
        fila = a * zona_b if zona_b is not None else 0.0
        try:
            from app.services import secoes_mf
            fila_max = secoes_mf.queue_cap(self.section_id) * 1.5
        except Exception:
            fila_max = float(self.capacidade)
        self.fila_estimada = max(0.0, min(fila_max, fila))

    def _decay(self, now_s: float) -> None:
        """0 nós online → fonte offline: decaimento exponencial (tau 20 min)."""
        if self.ocupacao is None or self.ts_estimativa is None:
            return
        dt = max(0.0, now_s - self.ts_estimativa)
        self.ocupacao = self.ocupacao * math.exp(-dt / max(DECAY_TAU_S, _EPS))
        self.ts_estimativa = float(now_s)
        self.fila_estimada = 0.0

    # — confiança cruzada —
    def confianca_cruzada(self, now_s: float) -> float:
        """(0.45·c1 + 0.35·c2 + 0.20·c3)/max(Σ pesos disponíveis, ε), ∈ [0,1]."""
        num, den = 0.0, 0.0
        if self.ts_cabeca is not None:
            idade_min = max(0.0, now_s - self.ts_cabeca) / 60.0
            c1 = math.exp(-idade_min / 15.0)
            num += PESO_C1 * c1
            den += PESO_C1
        if self.regressao.fitted:
            num += PESO_C2 * max(0.0, min(1.0, self.regressao.r2))
            den += PESO_C2
        nos_online = len(self._nos_online(now_s))
        c3 = nos_online / max(len(self.posicoes), 1)
        num += PESO_C3 * max(0.0, min(1.0, c3))
        den += PESO_C3
        conf = num / max(den, _EPS)
        if not math.isfinite(conf):
            conf = 0.0
        return round(max(0.0, min(1.0, conf)), 3)

    # — congestão parado-vs-fluir —
    def flag_congestao(self) -> bool:
        """True quando a secção está cheia (>0.75×cap) E o fluxo está PARADO:
        últimos ≥5 pontos de história com |delta ocupação| médio <1.0/ponto
        e ocupação média >0.75×cap. Multidão parada ≠ fila a fluir."""
        cap = max(float(self.capacidade), _EPS)
        ocup = float(self.ocupacao) if self.ocupacao is not None else 0.0
        if ocup / cap <= CONGESTAO_OCUP_RATIO:
            return False
        pts = list(self.historia)[-CONGESTAO_PONTOS_MIN:]
        if len(pts) < CONGESTAO_PONTOS_MIN:
            return False
        occs = [float(p.get("ocupacao") or 0.0) for p in pts]
        deltas = [abs(occs[i + 1] - occs[i]) for i in range(len(occs) - 1)]
        delta_medio = sum(deltas) / max(len(deltas), 1)
        ocup_media = sum(occs) / max(len(occs), 1)
        return (delta_medio < CONGESTAO_DELTA_MAX
                and ocup_media > CONGESTAO_OCUP_RATIO * cap)

    # — payload de estado —
    def payload(self, now_s: Optional[float] = None) -> dict:
        now_s = now_s if now_s is not None else time.time()
        nos_online = len(self._nos_online(now_s))
        # sem nós online há mais de um ciclo: aplica decaimento ao ler
        if nos_online == 0 and self.tem_dados:
            self._decay(now_s)
        idade = (round(max(0.0, now_s - self.ts_cabeca), 1)
                 if self.ts_cabeca is not None else None)
        congestao = self.flag_congestao()
        # transição False→True vai ao decision_log (uma vez por episódio)
        if congestao and not _CONGESTAO_PREV.get(self.section_id, False):
            try:
                from app.services import decision_log
                decision_log.log(
                    tipo="congestao", origem="motor", seccao=self.section_id,
                    depois={"ocupacao": round(self.ocupacao or 0.0, 1),
                            "capacidade": self.capacidade},
                    justificacao="multidão parada >75% da capacidade — "
                                 "fluxo sem variação em ≥5 pontos",
                )
            except Exception:
                pass
        _CONGESTAO_PREV[self.section_id] = congestao
        return {
            "cluster_id": self.cluster_id,
            "secao": self.secao,
            "ocupacao": round(self.ocupacao, 1) if self.ocupacao is not None else 0.0,
            "fila_estimada": round(self.fila_estimada, 1),
            "confianca_cruzada": self.confianca_cruzada(now_s),
            "a_actual": round(self.regressao.a, 3),
            "b_actual": round(self.regressao.b, 2),
            "r2": round(self.regressao.r2, 3),
            "pares_na_janela": len(self.regressao.pares),
            "idade_ancora_s": idade,
            "fonte_ancora": self.fonte_ancora,
            "nos_online": nos_online,
            "nos_totais": len(self.posicoes),
            "n_acessos": self.n_acessos,
            "flag_anomalia": bool(self.flag_anomalia),
            "flag_congestao": congestao,
            "nos_quarentena": sorted(self.quarentena),
            "ts_suspeitos": self._ts_suspeitos(),
            "capacidade": self.capacidade,
            "fonte_wifi": "online" if nos_online > 0 else "offline",
            "origem": self.origem,
            "surto_activo": _surge_factor(now_s) > 1.0,
            "pontos_memoria": len(self.historia),
        }

    def _ts_suspeitos(self) -> list[str]:
        """Ids com relógio suspeito: nós marcados + 'ancora' se for o caso."""
        ids = [nid for nid, rec in self.nos.items() if rec.get("ts_suspeito")]
        if self.ancora_ts_suspeita:
            ids.append("ancora")
        return sorted(ids)

    def history(self, n: int = HISTORIA_MAX) -> list[dict]:
        """Últimos n pontos da série temporal."""
        n = max(1, min(int(n), HISTORIA_MAX))
        return list(self.historia)[-n:]

    def regression_pairs(self) -> list[list[float]]:
        """Pares (w, c) da janela actual — para o scatter da regressão."""
        return [[round(p[1], 1), round(p[2], 1)] for p in self.regressao.pares]

    # — snapshot —
    def to_dict(self) -> dict:
        return {
            "regressao": self.regressao.to_dict(),
            "nos": {nid: dict(rec) for nid, rec in self.nos.items()},
            "c_ultima": self.c_ultima,
            "ts_cabeca": self.ts_cabeca,
            "wifi_na_ancora": self.wifi_na_ancora,
            "fonte_ancora": self.fonte_ancora,
            "ocupacao": self.ocupacao,
            "ts_estimativa": self.ts_estimativa,
            "fila_estimada": self.fila_estimada,
            "flag_anomalia": self.flag_anomalia,
            "tem_dados": self.tem_dados,
            "origem": self.origem,
            "quarentena": sorted(self.quarentena),
            "primeiro_desvio_ts": dict(self.primeiro_desvio_ts),
            "ancora_ts_suspeita": bool(self.ancora_ts_suspeita),
            "historia": list(self.historia)[-HISTORIA_SNAPSHOT:],
        }

    def restore(self, d: dict) -> None:
        try:
            a0 = A0_INTERIOR if is_interior_fechado(self.cluster_id) else A0_EXTERIOR
            self.regressao = RegressaoRolante.from_dict(d.get("regressao") or {}, a0)
            self.nos = {str(k): dict(v) for k, v in (d.get("nos") or {}).items()}
            self.c_ultima = d.get("c_ultima")
            self.ts_cabeca = d.get("ts_cabeca")
            self.wifi_na_ancora = d.get("wifi_na_ancora")
            self.fonte_ancora = d.get("fonte_ancora")
            self.ocupacao = d.get("ocupacao")
            self.ts_estimativa = d.get("ts_estimativa")
            self.fila_estimada = float(d.get("fila_estimada") or 0.0)
            self.flag_anomalia = bool(d.get("flag_anomalia", False))
            self.tem_dados = bool(d.get("tem_dados", False))
            self.origem = str(d.get("origem") or "real")
            self.quarentena = {str(n) for n in (d.get("quarentena") or [])}
            self.primeiro_desvio_ts = {
                str(k): float(v)
                for k, v in (d.get("primeiro_desvio_ts") or {}).items()
            }
            self.ancora_ts_suspeita = bool(d.get("ancora_ts_suspeita", False))
            self.historia = deque(
                [dict(p) for p in (d.get("historia") or [])],
                maxlen=HISTORIA_MAX,
            )
        except Exception as exc:
            _logger.debug("fusao_rolante restore %s erro (ignorado): %s",
                          self.section_id, exc)


# ── Registo global (em memória, single-process) ─────────────────────────────
_ESTIMADORES: dict[str, EstimadorSeccao] = {}


def _build_all() -> None:
    for sec in _sections_from_geo():
        if sec["section_id"] not in _ESTIMADORES:
            _ESTIMADORES[sec["section_id"]] = EstimadorSeccao(
                section_id=sec["section_id"],
                cluster_id=sec["cluster_id"],
                secao=sec["secao"],
                capacidade=sec["capacidade"],
                n_acessos=_n_acessos(sec["cluster_id"], sec["secao"]),
                posicoes=tuple(sec["posicoes"]),
            )


def section_id_for(cluster_id: str, secao: Optional[str]) -> Optional[str]:
    """Resolve (cluster, secao) → section_id. None se combinação inválida."""
    cid = cluster_id.lower()
    with _LOCK:
        _build_all()
        if cid in _ESTIMADORES:                      # unissexo: UMA secção
            return cid
        s = (secao or "").lower()
        sid = f"{cid}_{s}"
        return sid if sid in _ESTIMADORES else None


def get_estimador(section_id: str) -> Optional[EstimadorSeccao]:
    with _LOCK:
        _build_all()
        return _ESTIMADORES.get(section_id.lower())


def ingest_wifi_bandas(cluster_id: str, secao: Optional[str], no: str,
                       macs_a: int, macs_b: int,
                       ts_ms: Optional[int] = None,
                       origem: str = "real",
                       now_s: Optional[float] = None) -> Optional[dict]:
    """Regista um POST WiFi por bandas. Devolve payload da secção ou None.
    now_s é o "agora" da chamada (default time.time()) — ts desviado > 5 min
    marca o nó como ts_suspeito (S25) sem o fundir."""
    sid = section_id_for(cluster_id, secao)
    if sid is None:
        return None
    now_ref = float(now_s) if now_s is not None else time.time()
    ts_s = (ts_ms / 1000.0) if ts_ms else now_ref
    with _LOCK:
        est = _ESTIMADORES[sid]
        est.ingest_wifi(str(no), macs_a, macs_b, ts_s, origem=origem,
                        now_s=now_ref)
        # ts suspeito não pode servir de relógio ao payload
        ts_pay = ts_s if abs(ts_s - now_ref) <= TS_SKEW_MAX_S else now_ref
        return est.payload(ts_pay)


def ingest_cabecas(cluster_id: str, secao: Optional[str], cabecas: float,
                   fonte: str = "manual",
                   ts_ms: Optional[int] = None,
                   origem: str = "real",
                   now_s: Optional[float] = None) -> Optional[dict]:
    """Regista uma contagem de cabeças (âncora). Devolve payload ou None.
    now_s é o "agora" da chamada (default time.time()) — âncora com ts
    desviado > 5 min é aceite mas não re-baseia nem cria par (S25)."""
    sid = section_id_for(cluster_id, secao)
    if sid is None:
        return None
    now_ref = float(now_s) if now_s is not None else time.time()
    ts_s = (ts_ms / 1000.0) if ts_ms else now_ref
    with _LOCK:
        est = _ESTIMADORES[sid]
        est.ingest_cabecas(cabecas, fonte, ts_s, origem=origem, now_s=now_ref)
        ts_pay = ts_s if abs(ts_s - now_ref) <= TS_SKEW_MAX_S else now_ref
        return est.payload(ts_pay)


def remover_quarentena(section_id: str, no: str, utilizador: str) -> dict:
    """Tira um nó de quarentena (S24). PROIBIDO sem registo: exige utilizador
    e fica sempre no decision_log (origem=operador)."""
    if not utilizador or not str(utilizador).strip():
        raise ValueError("remover_quarentena exige utilizador — operação auditada")
    est = get_estimador(section_id)
    if est is None:
        raise ValueError(f"secção desconhecida: {section_id!r}")
    no = str(no)
    with _LOCK:
        estava = no in est.quarentena
        est.quarentena.discard(no)
        est.primeiro_desvio_ts.pop(no, None)
    from app.services import decision_log
    decision_log.log(
        tipo="quarentena_removida", origem="operador",
        utilizador=str(utilizador).strip(), seccao=est.section_id,
        antes={"no": no, "quarentena": estava},
        depois={"no": no, "quarentena": False},
        justificacao="remoção manual de quarentena pelo operador",
    )
    return {"section_id": est.section_id, "no": no, "removido": estava,
            "nos_quarentena": sorted(est.quarentena)}


def get_section_detail(section_id: str, n_history: int = 240,
                       now_s: Optional[float] = None) -> Optional[dict]:
    """Payload + memória + pares da regressão de uma secção."""
    est = get_estimador(section_id)
    if est is None:
        return None
    with _LOCK:
        return {
            "section_id": est.section_id,
            **est.payload(now_s),
            "historia": est.history(n_history),
            "pares_regressao": est.regression_pairs(),
        }


def node_live_state(now_s: Optional[float] = None) -> dict[str, dict]:
    """Estado ao vivo de cada nó WiFi conhecido: online, últimas contagens."""
    now_s = now_s if now_s is not None else time.time()
    out: dict[str, dict] = {}
    with _LOCK:
        _build_all()
        for est in _ESTIMADORES.values():
            for nid, rec in est.nos.items():
                age = max(0.0, now_s - rec["ts"])
                out[str(nid)] = {
                    "section_id": est.section_id,
                    "online": age <= NO_TTL_S,
                    "idade_s": round(age, 1),
                    "macs_A": rec.get("macs_A", 0),
                    "macs_B": rec.get("macs_B", 0),
                }
    return out


def get_section_payload(section_id: str,
                        now_s: Optional[float] = None) -> Optional[dict]:
    est = get_estimador(section_id)
    if est is None or not est.tem_dados:
        return None
    with _LOCK:
        return est.payload(now_s)


def get_cluster_payload(cluster_id: str,
                        now_s: Optional[float] = None) -> dict[str, dict]:
    """Secções de um cluster: {'m':…,'f':…} para MF, {'u':…} para unissexo."""
    cid = cluster_id.lower()
    out: dict[str, dict] = {}
    with _LOCK:
        _build_all()
        for sid, est in _ESTIMADORES.items():
            if est.cluster_id == cid and est.tem_dados:
                out[est.secao] = est.payload(now_s)
    return out


def get_all(now_s: Optional[float] = None) -> dict[str, dict]:
    with _LOCK:
        _build_all()
        return {sid: est.payload(now_s)
                for sid, est in _ESTIMADORES.items() if est.tem_dados}


def reset() -> None:
    """Limpa todo o estado (usado em testes)."""
    global _PG_EM_FALHA
    with _LOCK:
        _ESTIMADORES.clear()
        _CONGESTAO_PREV.clear()
        _PENDENTES.clear()
        _PG_EM_FALHA = False


# ── Snapshot Postgres (mesmo padrão do ingest_store) ────────────────────────
# BUFFER LOCAL (S13): se o Postgres cair, os snapshots ficam aqui em anel e
# são reconciliados na próxima persistência bem-sucedida.
_PENDENTES: deque = deque(maxlen=30)    # {"ts": s, "snap": {sid: estado}}
_PG_EM_FALHA = False                    # já estamos em modo degradado?


async def _persist_snapshot(session_factory) -> None:
    """Persiste o estado das secções em fusao_rolante_snapshots. Se o Postgres
    cair, guarda o snap em _PENDENTES (S13) e regista modo_degradado UMA vez
    (só na transição para falha)."""
    global _PG_EM_FALHA
    snap: dict = {}
    try:
        from app.models.db.operations import FusaoRolanteSnapshot

        with _LOCK:
            snap = {sid: est.to_dict() for sid, est in _ESTIMADORES.items()
                    if est.tem_dados}

        if not snap and _PENDENTES:
            # nada novo em memória mas há buffer: reconcilia o mais recente
            snap = max(_PENDENTES, key=lambda p: p["ts"])["snap"]
        if not snap:
            return
        async with session_factory() as session:
            now_ms = int(time.time() * 1000)
            for sid, state in snap.items():
                existing = await session.get(FusaoRolanteSnapshot, sid)
                if existing:
                    existing.state_json = state
                    existing.ts_server = now_ms
                else:
                    session.add(FusaoRolanteSnapshot(
                        section_id=sid, state_json=state, ts_server=now_ms,
                    ))
            await session.commit()
        # sucesso: o snap escrito é o mais recente — buffer reconciliado
        if _PENDENTES:
            _PENDENTES.clear()
            _logger.info("fusao_rolante: buffer local reconciliado no Postgres")
        _PG_EM_FALHA = False
    except Exception as exc:
        if snap:
            _PENDENTES.append({"ts": time.time(), "snap": snap})
        if not _PG_EM_FALHA:
            # decision_log apenas na TRANSIÇÃO para falha — não a cada tentativa
            _PG_EM_FALHA = True
            try:
                from app.services import decision_log
                decision_log.log(
                    tipo="modo_degradado", origem="motor",
                    justificacao="Postgres indisponível — snapshot em buffer local",
                )
            except Exception:
                pass
        _logger.debug("fusao_rolante snapshot erro (buffer local): %s", exc)


async def _load_snapshot(session_factory) -> None:
    """Ao iniciar, recarrega o estado a partir de fusao_rolante_snapshots.

    MEMÓRIA ENTRE DIAS (S23): snapshots antigos (>24h) NÃO são descartados —
    restauram-se SEMPRE por inteiro. Os pares (w, c) com mais de 3 horas
    expiram naturalmente na próxima add_pair (janela rolante), mas o a/b/r2
    aprendidos FICAM: o dia 3 do festival arranca com o declive calibrado
    nos dias 1 e 2, em vez de voltar ao a0 por defeito.
    """
    try:
        from sqlalchemy import select as _select
        from app.models.db.operations import FusaoRolanteSnapshot

        async with session_factory() as session:
            result = await session.execute(_select(FusaoRolanteSnapshot))
            rows = result.scalars().all()
            if not rows:
                return
            with _LOCK:
                _build_all()
                for row in rows:
                    est = _ESTIMADORES.get(row.section_id)
                    if est is not None:
                        est.restore(dict(row.state_json or {}))
            _logger.info("fusao_rolante: %d secções recarregadas do snapshot",
                         len(rows))
    except Exception as exc:
        _logger.debug("fusao_rolante load snapshot erro (ignorado): %s", exc)


async def snapshot_loop(session_factory, interval_s: float = 60.0) -> None:
    """Loop assíncrono: persiste snapshot a cada interval_s segundos."""
    while True:
        await asyncio.sleep(interval_s)
        await _persist_snapshot(session_factory)
