"""
PlantaOS — Caminho mais leve (onda 8a): o motor DECIDE, a IA só narra.

GET /api/v1/route?origem=&genero= → top-3 secções permitidas, custo DECOMPOSTO:
  {wc, tipo, caminhada_min, fila_min, congestao, surto, confianca, total_min}

- Caminhada por DIJKSTRA no grafo de corredores (NUNCA euclidiana directa);
  vizinhanças confirmadas: WC-01↔WC-08 e WC-01↔WC-02. Coordenadas e
  distâncias SEMPRE de clusters_geo.distance_m.
- Género: F só vê secções F + unissexo; M só M + unissexo. NUNCA cruzar.
- ANTI-MANADA: quota proporcional a folga² (folga = serviço×8min − fila);
  o ecrã público mostra 2-3 opções, nunca argmin-para-todos.
- HISTERESE: a recomendação principal só muda com ganho >20% E ≥3 min
  de permanência (campo recomendado_desde_s). Trocas vão ao decision_log.
- PRÉ-SURTO: T-10 min do fim do headliner (de /shows) penaliza clusters
  próximos do palco.
- Cache 10 s por (origem, género). Cluster fechado excluído no mesmo tick.
- Fallback narrativo determinista: frase-template do próprio top-3
  (PT-PT + EN) — o ecrã nunca fica vazio nem espera pela IA.
"""
from __future__ import annotations

import heapq
import threading
import time
from typing import Optional

from app.clusters_geo import CLUSTERS_GEO, LANDMARKS, distance_m

VELOCIDADE_M_MIN = 70.0          # passo em multidão (~4.2 km/h)
FOLGA_HORIZONTE_MIN = 8.0        # folga = serviço×8min − fila
HISTERESE_GANHO = 0.20           # só troca com ganho >20%…
HISTERESE_MIN_S = 180.0          # …e ≥3 min de permanência
PRE_SURTO_S = 10 * 60.0          # T-10 min do fim do headliner
PRE_SURTO_PENAL_MIN = 4.0        # penalização máxima (cluster colado ao palco)
SAIDA_JANELA_S = 90 * 60.0       # modo saída: até 90 min após o último show
SAIDA_BONUS_MIN = 1.5            # bónus (custo negativo) perto da ENTRADA
SAIDA_DIST_M = 150.0             # "perto da ENTRADA" = <150 m no grafo geo
CONGESTAO_PARADA_MIN = 2.0       # penalização multidão parada (flag_congestao)
CACHE_TTL_S = 10.0
_EPS = 0.001

# ── Grafo de corredores (arestas cortáveis; distâncias de clusters_geo) ─────
# Vizinhanças CONFIRMADAS pelo Gonçalo: WC-01↔WC-08 e WC-01↔WC-02
# (WC-08 é vizinho da zona alta, não posto isolado).
_ADJ: dict[str, list[str]] = {
    "WC-01": ["WC-02", "WC-08"],
    "WC-02": ["WC-01", "WC-04", "WC-05"],
    "WC-03": ["WC-05", "WC-07"],
    "WC-04": ["WC-02", "WC-05"],
    "WC-05": ["WC-02", "WC-03", "WC-04", "WC-07"],
    "WC-06": ["WC-07", "WC-08"],
    "WC-07": ["WC-03", "WC-05", "WC-06"],
    "WC-08": ["WC-01", "WC-06"],
}
# Landmarks ligados aos clusters mais próximos (entradas no grafo)
_LANDMARK_ADJ: dict[str, list[str]] = {
    "ENTRADA": ["WC-03", "WC-05"],
    "PALCO_MUNDO": ["WC-06", "WC-07"],
    "MUSIC_VALLEY": ["WC-06", "WC-08"],
    "SUPER_BOCK": ["WC-06", "WC-07"],
}

_GEO = {c["id"]: c for c in CLUSTERS_GEO}
_LM = {l["id"]: l for l in LANDMARKS}


def _dist(a: str, b: str) -> float:
    """Distância entre dois nós do grafo (cluster ou landmark), em metros."""
    def pos(n: str) -> tuple[float, float]:
        if n in _GEO:
            return _GEO[n]["e_m"], _GEO[n]["n_m"]
        l = _LM[n]
        return l["e_m"], l["n_m"]
    if a in _GEO and b in _GEO:
        return distance_m(a, b)
    (ea, na), (eb, nb) = pos(a), pos(b)
    return round(((ea - eb) ** 2 + (na - nb) ** 2) ** 0.5, 1)


def _edges() -> dict[str, list[tuple[str, float]]]:
    g: dict[str, list[tuple[str, float]]] = {}
    for a, viz in _ADJ.items():
        for b in viz:
            g.setdefault(a, []).append((b, _dist(a, b)))
    for lm, viz in _LANDMARK_ADJ.items():
        for b in viz:
            d = _dist(lm, b)
            g.setdefault(lm, []).append((b, d))
            g.setdefault(b, []).append((lm, d))
    return g


def dijkstra_min(origem: str, pcd: bool = False) -> dict[str, float]:
    """Minutos a pé da origem a cada cluster, pelo grafo de corredores.

    Velocidade POR ARESTA (ambiente): lama ⇒ ~46.7 m/min (0.8 m/s vs 1.2 m/s);
    arestas "cortada" são excluídas do grafo (S09). pcd=True exclui TAMBÉM
    as arestas em lama — PROIBIDO oferecer a PCD caminho com lama (S02)."""
    g = _edges()
    try:
        from app.services import ambiente
        lama = ambiente.arestas_em_lama()
        cortadas = ambiente.arestas_cortadas()
        vel_lama = VELOCIDADE_M_MIN * ambiente.FACTOR_LAMA
    except Exception:
        lama, cortadas, vel_lama = set(), set(), VELOCIDADE_M_MIN
    o = origem.upper()
    if o not in g:
        o = "ENTRADA"
    # dist em MINUTOS (a velocidade varia por aresta)
    dist: dict[str, float] = {o: 0.0}
    pq: list[tuple[float, str]] = [(0.0, o)]
    while pq:
        d, n = heapq.heappop(pq)
        if d > dist.get(n, float("inf")):
            continue
        for viz, w in g.get(n, ()):
            aid = "|".join(sorted((n, viz)))
            if aid in cortadas:
                continue                      # aresta cortada sai do grafo
            if aid in lama:
                if pcd:
                    continue                  # PCD NUNCA passa por lama
                vel = vel_lama
            else:
                vel = VELOCIDADE_M_MIN
            nd = d + w / max(vel, _EPS)
            if nd < dist.get(viz, float("inf")):
                dist[viz] = nd
                heapq.heappush(pq, (nd, viz))
    return {n: round(d, 1) for n, d in dist.items() if n in _GEO}


# ── Pré-surto (T-10 min do fim do headliner) ────────────────────────────────
def _pre_surto(now_s: float) -> Optional[str]:
    """Devolve o palco do headliner se faltarem ≤10 min para o fim."""
    try:
        from datetime import datetime
        from app.services.state import get_shows
        for show in get_shows():
            if not show.headliner:
                continue
            end_s = datetime.fromisoformat(show.end_iso).timestamp()
            if 0.0 <= end_s - now_s <= PRE_SURTO_S:
                return show.stage
        return None
    except Exception:
        return None


_STAGE_LM = {"Palco Mundo": "PALCO_MUNDO", "Super Bock Stage": "SUPER_BOCK",
             "Music Valley": "MUSIC_VALLEY"}


# ── Modo saída (após o fim do ÚLTIMO show do dia) ───────────────────────────
_MODO_SAIDA_ULT: Optional[bool] = None     # último estado (para log de transição)


def _modo_saida(now_s: float) -> bool:
    """True se o último show (max end_iso) terminou há <90 min — a multidão
    flui para a ENTRADA; clusters perto da saída ganham bónus."""
    try:
        from datetime import datetime
        from app.services.state import get_shows
        fins = [datetime.fromisoformat(s.end_iso).timestamp()
                for s in get_shows()]
        if not fins:
            return False
        ultimo = max(fins)
        return 0.0 < now_s - ultimo < SAIDA_JANELA_S
    except Exception:
        return False


def _modo_saida_com_log(now_s: float) -> bool:
    """Detecta o modo saída e regista a TRANSIÇÃO no decision_log."""
    global _MODO_SAIDA_ULT
    activo = _modo_saida(now_s)
    anterior = bool(_MODO_SAIDA_ULT) if _MODO_SAIDA_ULT is not None else False
    if activo != anterior:
        try:
            from app.services import decision_log
            decision_log.log(
                tipo="modo_saida", origem="motor",
                antes={"activo": anterior}, depois={"activo": activo},
                justificacao="fim do último show há <90 min — bónus a "
                             "clusters perto da ENTRADA" if activo
                             else "janela de saída terminou",
            )
        except Exception:
            pass
    _MODO_SAIDA_ULT = activo
    return activo


def _penal_surto(cluster_id: str, palco: Optional[str]) -> float:
    """Penaliza clusters próximos do palco em pré-surto (0..PRE_SURTO_PENAL)."""
    if not palco:
        return 0.0
    lm = _STAGE_LM.get(palco)
    if not lm or lm not in _LM:
        return 0.0
    d = _dist(cluster_id.upper(), lm)
    span = 300.0
    return round(PRE_SURTO_PENAL_MIN * max(0.0, 1.0 - d / span), 1)


# ── Histerese por (origem, género) ──────────────────────────────────────────
_LOCK = threading.Lock()
# key -> {"wc": section_id, "desde_s": float, "total": float}
_RECOMENDADO: dict[str, dict] = {}
_CACHE: dict[str, tuple[float, dict]] = {}


def compute_route(origem: str, genero: str,
                  now_s: Optional[float] = None, pcd: bool = False) -> dict:
    """Top-3 secções permitidas com custo decomposto + histerese + quotas.
    pcd=True: caminhadas SEM arestas em lama (S02)."""
    t = now_s if now_s is not None else time.time()
    key = f"{origem.upper()}|{(genero or 'f').lower()[:1]}|{int(bool(pcd))}"

    with _LOCK:
        hit = _CACHE.get(key)
        if hit and now_s is None and t - hit[0] < CACHE_TTL_S:
            return hit[1]

    from app.services import fusao_rolante, secoes_mf
    walk = dijkstra_min(origem, pcd=pcd)
    palco_surto = _pre_surto(t)
    modo_saida = _modo_saida_com_log(t)
    estado = fusao_rolante.get_all(now_s=t if now_s is not None else None)

    opcoes = []
    for sid in secoes_mf.seccoes_permitidas(genero):
        cid = sid.split("_")[0]
        p = estado.get(sid) or {}
        fila = float(p.get("fila_estimada") or 0.0)
        conf = float(p.get("confianca_cruzada") or 0.0)
        ocup = float(p.get("ocupacao") or 0.0)
        cap = max(float(p.get("capacidade") or secoes_mf.posicoes(sid)), 1.0)

        caminhada = walk.get(cid.upper(), 9.9)
        fila_min = secoes_mf.espera_prevista_min(sid, fila)
        congestao = round(2.0 * max(0.0, ocup / cap - 0.7) / 0.3, 1)
        # multidão parada ≠ fila a fluir: flag_congestao penaliza +2 min
        if p.get("flag_congestao"):
            congestao = round(congestao + CONGESTAO_PARADA_MIN, 1)
        surto = _penal_surto(cid, palco_surto)
        penal_conf = round(1.5 * (1.0 - min(1.0, conf)), 1) if p else 0.5
        total = round(caminhada + min(fila_min, 99.0) + congestao
                      + surto + penal_conf, 1)
        # MODO SAÍDA: bónus a clusters perto da ENTRADA (a multidão sai)
        if modo_saida:
            try:
                if _dist(cid.upper(), "ENTRADA") < SAIDA_DIST_M:
                    total = round(max(0.1, total - SAIDA_BONUS_MIN), 1)
            except Exception:
                pass
        servico = secoes_mf.servico_pmin(sid)
        folga = max(0.0, servico * FOLGA_HORIZONTE_MIN - fila)
        opcoes.append({
            "wc": sid,
            "tipo": "unissexo" if "_" not in sid else sid.split("_")[1].upper(),
            "caminhada_min": caminhada,
            "fila_min": min(fila_min, 99.0),
            "congestao": congestao,
            "surto": surto,
            "confianca": round(conf, 3),
            "total_min": total,
            "_folga": folga,
        })

    opcoes.sort(key=lambda o: o["total_min"])
    top = opcoes[:3]

    # ANTI-MANADA: quota proporcional a folga² (nunca argmin para todos)
    soma_f2 = sum(o["_folga"] ** 2 for o in top)
    for o in top:
        o["quota_pct"] = round(100.0 * (o["_folga"] ** 2) / max(soma_f2, _EPS), 1) \
            if soma_f2 > 0 else round(100.0 / max(len(top), 1), 1)
        del o["_folga"]

    # HISTERESE: só troca com ganho >20% E ≥3 min de permanência
    with _LOCK:
        atual = _RECOMENDADO.get(key)
        escolhido = top[0] if top else None
        if escolhido is not None and atual is not None:
            ainda_existe = next((o for o in top if o["wc"] == atual["wc"]), None)
            permanencia = t - atual["desde_s"]
            if ainda_existe is not None and escolhido["wc"] != atual["wc"]:
                ganho = (ainda_existe["total_min"] - escolhido["total_min"]) \
                    / max(ainda_existe["total_min"], _EPS)
                if ganho <= HISTERESE_GANHO or permanencia < HISTERESE_MIN_S:
                    escolhido = ainda_existe       # mantém — sem flip-flop
        if escolhido is not None:
            if atual is None or atual["wc"] != escolhido["wc"]:
                if atual is not None:
                    try:
                        from app.services import decision_log
                        decision_log.log(
                            tipo="troca_recomendacao", origem="motor",
                            seccao=escolhido["wc"],
                            antes={"wc": atual["wc"], "total": atual["total"]},
                            depois={"wc": escolhido["wc"],
                                    "total": escolhido["total_min"]},
                            justificacao="ganho >20% com ≥3 min de permanência",
                        )
                    except Exception:
                        pass
                _RECOMENDADO[key] = {"wc": escolhido["wc"], "desde_s": t,
                                     "total": escolhido["total_min"]}
            else:
                _RECOMENDADO[key]["total"] = escolhido["total_min"]
            # recomendação primeiro, restantes pela ordem de custo
            top = [escolhido] + [o for o in top if o["wc"] != escolhido["wc"]]
        desde = _RECOMENDADO.get(key, {}).get("desde_s", t)

    result = {
        "origem": origem.upper(),
        "genero": (genero or "f").lower()[:1],
        "opcoes": top,
        "recomendado": top[0]["wc"] if top else None,
        "recomendado_desde_s": round(t - desde, 1),
        "pre_surto": palco_surto,
        "pcd": bool(pcd),
        "modo_saida": modo_saida,
        "narrativa": _narrativa(top, palco_surto),
        "ts": t,
    }
    with _LOCK:
        _CACHE[key] = (t, result)
    return result


def _narrativa(top: list[dict], palco_surto: Optional[str]) -> dict:
    """Fallback determinista (PT-PT 3 frases + 1 EN) — nunca ecrã vazio."""
    if not top:
        return {"pt": "Sem casas-de-banho disponíveis neste momento. "
                      "Procura um steward. Obrigado pela paciência.",
                "en": "No restrooms available right now — please ask a steward."}
    o1 = top[0]
    nome1 = o1["wc"].upper().replace("_M", " (Masc.)").replace("_F", " (Fem.)")
    pt = (f"Recomendamos o {nome1}: {o1['caminhada_min']:g} min a pé e "
          f"~{o1['fila_min']:g} min de fila — é o caminho mais leve agora. ")
    if len(top) > 1:
        o2 = top[1]
        nome2 = o2["wc"].upper().replace("_M", " (Masc.)").replace("_F", " (Fem.)")
        pt += (f"Alternativa: {nome2} a {o2['caminhada_min']:g} min. ")
    pt += ("O intervalo é agora — evita a saída do palco. "
           if palco_surto else "Boa rota e bom festival. ")
    en = (f"Best option: {nome1} — {o1['caminhada_min']:g} min walk, "
          f"~{o1['fila_min']:g} min queue.")
    return {"pt": pt.strip(), "en": en}


def reset() -> None:
    global _MODO_SAIDA_ULT
    with _LOCK:
        _RECOMENDADO.clear()
        _CACHE.clear()
        _MODO_SAIDA_ULT = None
