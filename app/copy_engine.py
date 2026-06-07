"""
PlantaOS — Motor de Copy Contextual (Screen Copy Engine)
=========================================================
Olha para os 8 clusters EM CONJUNTO, compara-os, e escolhe a melhor frase
para cada secção (M / F / unissexo), naquele instante, bilingue PT-PT + EN.

NÃO são frases fixas: reagem ao estado RELATIVO de todos os WC.
Ex.: "se este WC está vazio e o vizinho cheio → manda a malta para cá."

Princípios:
  - Determinístico (mesma entrada → mesma frase), mas roda dentro do pool
    via um índice que avança no tempo, para não repetir.
  - Honesto: se a leitura não é fiável (offline/baixa confiança), diz-se
    de forma neutra; NUNCA inventa números nem mostra "SIMULADO".
  - M e F podem ter frases diferentes.
  - Cor crítica é âmbar (decidido no frontend); aqui só devolvemos texto+tom.

Contrato:
  build_copy(clusters: list[ClusterSnapshot], now_ms: int) -> dict[str, SectionCopy]
  onde a chave é o section_id ("wc-01_m", "wc-01_f", "wc-05_u", ...).

Sem dependências externas. Testável isoladamente.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Contratos de dados
# ─────────────────────────────────────────────────────────────────────────────
Tom = Literal["vazio", "livre", "enchendo", "cheio", "limite", "neutro"]


@dataclass
class SectionInput:
    """Estado de UMA secção (lado M, lado F, ou unissexo)."""
    section_id: str          # "wc-01_m" | "wc-01_f" | "wc-05_u"
    cluster_id: str          # "wc-01"
    seccao: str              # "m" | "f" | "u"
    ocupacao_pct: float      # 0..100
    fila: int                # pessoas em fila
    espera_min: float        # minutos estimados
    fluxo_pmin: float        # entradas por minuto
    confianca: float         # 0..1
    live: bool               # fonte viva?
    is_unissex: bool


@dataclass
class ClusterSnapshot:
    """Um cluster com as suas secções (1 ou 2)."""
    cluster_id: str          # "wc-01"
    seccoes: list[SectionInput]


@dataclass
class SectionCopy:
    """Saída: a frase escolhida para uma secção."""
    section_id: str
    pt: str
    en: str
    tom: Tom


# ─────────────────────────────────────────────────────────────────────────────
# Metadados de cada cluster (contexto físico — usado nas frases)
# ─────────────────────────────────────────────────────────────────────────────
CLUSTER_META: dict[str, dict[str, str]] = {
    "wc-01": {"zona_pt": "Entrada Norte", "zona_en": "North Gate",
              "nota_pt": "perto da entrada", "nota_en": "near the gate"},
    "wc-02": {"zona_pt": "Palco Super Bock", "zona_en": "Super Bock Stage",
              "nota_pt": "colado ao palco", "nota_en": "right by the stage"},
    "wc-03": {"zona_pt": "Entrada Principal", "zona_en": "Main Gate",
              "nota_pt": "o primeiro à entrada", "nota_en": "first one in"},
    "wc-04": {"zona_pt": "Zona Alta", "zona_en": "Upper Area",
              "nota_pt": "no topo, com vista", "nota_en": "up top, with a view"},
    "wc-05": {"zona_pt": "Encosta", "zona_en": "Hillside",
              "nota_pt": "entrada única", "nota_en": "single entrance"},
    "wc-06": {"zona_pt": "Palco Bacana Play", "zona_en": "Bacana Play Stage",
              "nota_pt": "o maior do festival", "nota_en": "the biggest one"},
    "wc-07": {"zona_pt": "Lockers", "zona_en": "Lockers",
              "nota_pt": "ao pé dos cacifos", "nota_en": "by the lockers"},
    "wc-08": {"zona_pt": "Sul", "zona_en": "South",
              "nota_pt": "longe da multidão", "nota_en": "away from the crowd"},
}

ALL_CLUSTERS = list(CLUSTER_META.keys())


# ─────────────────────────────────────────────────────────────────────────────
# Limiares (legíveis, ajustáveis)
# ─────────────────────────────────────────────────────────────────────────────
VAZIO = 2.0       # < 2%  → praticamente vazio
MUITO_LIVRE = 25.0
LIVRE = 50.0
ENCHENDO = 70.0
CHEIO = 85.0
LIMITE = 95.0

CONF_BAIXA = 0.35   # abaixo disto, leitura pouco fiável
GAP_MF = 25.0       # diferença M vs F (em pontos %) para ser "notável"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de comparação entre clusters
# ─────────────────────────────────────────────────────────────────────────────
def _label(cluster_id: str) -> str:
    """'wc-01' -> 'WC-01'."""
    return cluster_id.upper()


def _section_worst(sec: SectionInput) -> float:
    return sec.ocupacao_pct


def _most_free_cluster(clusters: list[ClusterSnapshot], exclude: str) -> Optional[str]:
    """Cluster com a secção mais vazia (e fiável), excluindo um."""
    best_id, best_pct = None, 101.0
    for c in clusters:
        if c.cluster_id == exclude:
            continue
        for s in c.seccoes:
            if not s.live:
                continue
            if s.ocupacao_pct < best_pct:
                best_pct, best_id = s.ocupacao_pct, c.cluster_id
    return best_id


def _rank_among_all(sec: SectionInput, clusters: list[ClusterSnapshot]) -> tuple[int, int]:
    """Posição desta secção entre TODAS as secções vivas (1 = mais vazia)."""
    live_pcts = []
    for c in clusters:
        for s in c.seccoes:
            if s.live:
                live_pcts.append((s.section_id, s.ocupacao_pct))
    if not live_pcts:
        return (0, 0)
    live_pcts.sort(key=lambda x: x[1])
    total = len(live_pcts)
    pos = next((i + 1 for i, (sid, _) in enumerate(live_pcts) if sid == sec.section_id), 0)
    return (pos, total)


def _rotate(pool: list[tuple[str, str]], now_ms: int, salt: int) -> tuple[str, str]:
    """Escolhe uma frase do pool, rodando a cada ~11s (determinístico)."""
    if not pool:
        return ("", "")
    idx = (now_ms // 11000 + salt) % len(pool)
    return pool[idx]


def _seed(section_id: str) -> int:
    """Sal estável por secção, para M e F não rodarem em sincronia."""
    return sum(ord(c) for c in section_id)


# ─────────────────────────────────────────────────────────────────────────────
# POOLS DE FRASES — por tom, com variantes M / F / unissexo onde faz sentido
# Cada entrada: (pt, en). PT-PT seco, com humor inteligente. EN equivalente.
# ─────────────────────────────────────────────────────────────────────────────

# Quando a leitura não é fiável — honesto, sem números
POOL_NEUTRO: list[tuple[str, str]] = [
    ("A afinar a leitura.", "Reading settling."),
    ("Um instante — a calibrar.", "One sec — calibrating."),
    ("A acertar os sensores.", "Tuning the sensors."),
]

# VAZIO (<2%)
POOL_VAZIO = [
    ("Cabines à espera. Sem alma viva.", "Stalls waiting. Not a soul."),
    ("Vazio total. Entra como quem manda.", "Bone empty. Walk right in."),
    ("Zero pessoas. Zero desculpas.", "Zero people. Zero excuses."),
]
POOL_VAZIO_M = [
    ("Lado dos homens: deserto. Aproveita.", "Men's side: a desert. Make the most of it."),
    ("Eles ainda não chegaram. Tu chegaste.", "The guys aren't here yet. You are."),
]
POOL_VAZIO_F = [
    ("Lado delas: livre de ponta a ponta.", "Women's side: clear end to end."),
    ("Sem fila, sem espera, sem drama.", "No queue, no wait, no drama."),
]

# MUITO LIVRE (2–25%)
POOL_MUITO_LIVRE = [
    ("Quase só para ti. Despacha.", "Almost all yours. Be quick."),
    ("Espaço de sobra. Entra e sai.", "Room to spare. In and out."),
    ("Tranquilo. O momento é este.", "Calm. Now's the time."),
]

# LIVRE (25–50%)
POOL_LIVRE = [
    ("Ritmo calmo. Sem fila à vista.", "Easy pace. No queue in sight."),
    ("A fluir. Entra sem pensar.", "Flowing. Just walk in."),
    ("Espera de café. Curta.", "Coffee-break wait. Short."),
]

# ENCHENDO (50–70%)
POOL_ENCHENDO = [
    ("A encher, mas ainda anda.", "Filling up, but still moving."),
    ("Movimento bom. Vai dando.", "Good flow. It works."),
    ("Meio cheio. Ainda vale a pena.", "Half full. Still worth it."),
]

# CHEIO (70–85%)
POOL_CHEIO = [
    ("Cheio, mas a mexer.", "Busy, but moving."),
    ("Há fila. Vale a pena olhar à volta.", "There's a queue. Worth a look around."),
]

# LIMITE (>85%) — aqui sugerimos alternativa por nome
POOL_LIMITE = [
    ("No limite. {alt} respira melhor.", "Maxed out. {alt} breathes easier."),
    ("À pinha. Tenta {alt}.", "Packed. Try {alt}."),
    ("Pico aqui. {alt} a {dist}.", "Peak here. {alt} nearby."),
]
POOL_LIMITE_SEM_ALT = [
    ("No limite — como tudo agora. Aguenta.", "Maxed out — like everywhere now. Hang in."),
    ("À pinha. Respira, já passa.", "Packed. Breathe, it'll pass."),
]

# Comparação: este vazio, vizinho cheio
POOL_REFUGIO = [
    ("Enquanto {outro} está à pinha, aqui é livre.", "While {outro} is packed, here's open."),
    ("Foge da fila do {outro}. Aqui há lugar.", "Skip the {outro} queue. Room here."),
    ("O segredo: {outro} cheio, este vazio.", "The secret: {outro} full, this one empty."),
]

# É o mais vazio de todos
POOL_MAIS_VAZIO = [
    ("O mais livre do recinto. Agora.", "The freest spot on site. Right now."),
    ("Nenhum WC está mais à vontade que este.", "No WC is comfier than this one."),
]

# Diferença M vs F
POOL_M_MAIS_CHEIO = [
    ("Lado deles cheio, lado delas a respirar.", "Men's side full, women's breathing."),
    ("Eles em fila, elas à vontade.", "Guys queueing, gals cruising."),
]
POOL_F_MAIS_CHEIO = [
    ("Lado delas cheio, lado deles a respirar.", "Women's side full, men's breathing."),
    ("Elas em fila, eles à vontade.", "Gals queueing, guys cruising."),
]

# Fluxo: pico de entrada
POOL_PICO = [
    ("Toda a gente teve a mesma ideia agora.", "Everyone had the same idea just now."),
    ("Onda a chegar. Talvez espera dois minutos.", "Wave incoming. Maybe wait a couple."),
]
# Fluxo: a esvaziar
POOL_ESVAZIANDO = [
    ("A maré está a virar. Bom momento.", "Tide's turning. Good moment."),
    ("A esvaziar. Aproveita a janela.", "Emptying out. Grab the window."),
]


# ─────────────────────────────────────────────────────────────────────────────
# Decisão por secção (a árvore de prioridades)
# ─────────────────────────────────────────────────────────────────────────────
def _choose_for_section(
    sec: SectionInput,
    cluster: ClusterSnapshot,
    clusters: list[ClusterSnapshot],
    now_ms: int,
) -> SectionCopy:
    salt = _seed(sec.section_id)
    meta = CLUSTER_META.get(sec.cluster_id, {})

    def out(pool, tom: Tom, **fmt) -> SectionCopy:
        pt, en = _rotate(pool, now_ms, salt)
        if fmt:
            pt = pt.format(**fmt)
            en = en.format(**{k: v for k, v in fmt.items()})
        return SectionCopy(sec.section_id, pt, en, tom)

    # PRIORIDADE 0 — leitura não fiável → honesto, neutro
    if (not sec.live) or sec.confianca < CONF_BAIXA:
        return out(POOL_NEUTRO, "neutro")

    pct = sec.ocupacao_pct

    # PRIORIDADE 1 — comparação M vs F dentro do mesmo cluster (só M/F)
    if not sec.is_unissex:
        outra = next((s for s in cluster.seccoes if s.seccao != sec.seccao and s.live), None)
        if outra is not None:
            diff = sec.ocupacao_pct - outra.ocupacao_pct
            # esta secção está MUITO mais cheia que a outra
            if diff >= GAP_MF and pct >= ENCHENDO:
                # o lado cheio é ESTE; a frase nomeia quem está cheio
                pool = POOL_M_MAIS_CHEIO if sec.seccao == "m" else POOL_F_MAIS_CHEIO
                return out(pool, "cheio")
            # esta está MUITO mais vazia → o lado cheio é o OUTRO
            if -diff >= GAP_MF and pct < LIVRE:
                # nomear quem está cheio = a outra secção
                pool = POOL_M_MAIS_CHEIO if outra.seccao == "m" else POOL_F_MAIS_CHEIO
                return out(pool, "livre")

    # PRIORIDADE 2 — este vazio E existe vizinho cheio → refúgio
    if pct < MUITO_LIVRE:
        # há algum outro cluster no limite?
        cheio_outro = None
        for c in clusters:
            if c.cluster_id == sec.cluster_id:
                continue
            for s in c.seccoes:
                if s.live and s.ocupacao_pct >= CHEIO:
                    cheio_outro = c.cluster_id
                    break
            if cheio_outro:
                break
        if cheio_outro:
            return out(POOL_REFUGIO, "livre", outro=_label(cheio_outro))

    # PRIORIDADE 3 — é o mais vazio de todos?
    pos, total = _rank_among_all(sec, clusters)
    if total >= 3 and pos == 1 and pct < LIVRE:
        return out(POOL_MAIS_VAZIO, "livre")

    # PRIORIDADE 4 — fluxo (pico / esvaziar) quando em zona média
    if ENCHENDO <= pct < CHEIO:
        if sec.fluxo_pmin >= 8:
            return out(POOL_PICO, "cheio")
        if sec.fluxo_pmin <= -4:
            return out(POOL_ESVAZIANDO, "enchendo")

    # PRIORIDADE 5 — estado próprio (escada de ocupação)
    if pct < VAZIO:
        if sec.is_unissex:
            return out(POOL_VAZIO, "vazio")
        pool = POOL_VAZIO_M if sec.seccao == "m" else POOL_VAZIO_F
        return out(pool, "vazio")
    if pct < MUITO_LIVRE:
        return out(POOL_MUITO_LIVRE, "livre")
    if pct < LIVRE:
        return out(POOL_LIVRE, "livre")
    if pct < ENCHENDO:
        return out(POOL_ENCHENDO, "enchendo")
    if pct < CHEIO:
        return out(POOL_CHEIO, "cheio")

    # PRIORIDADE 6 — no limite → sugere alternativa por nome
    alt = _most_free_cluster(clusters, exclude=sec.cluster_id)
    if alt is not None:
        alt_meta = CLUSTER_META.get(alt, {})
        return out(POOL_LIMITE, "limite",
                   alt=_label(alt),
                   dist=alt_meta.get("nota_pt", "perto"))
    return out(POOL_LIMITE_SEM_ALT, "limite")


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────
def build_copy(clusters: list[ClusterSnapshot], now_ms: int) -> dict[str, SectionCopy]:
    """
    Recebe os 8 clusters e devolve, por section_id, a frase escolhida.
    Esta é a função que o endpoint/serviço chama.
    """
    result: dict[str, SectionCopy] = {}
    for c in clusters:
        for s in c.seccoes:
            result[s.section_id] = _choose_for_section(s, c, clusters, now_ms)
    return result
