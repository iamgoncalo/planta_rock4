"""
PlantaOS — Capacidades dos 8 clusters de WC (FONTE DE VERDADE UNICA).
Editar AQUI e so aqui. Usado por fusao, KPIs e ocupacao.
Capacidade = lugares simultaneos DENTRO do WC (masc + fem). ESPERA = antecamara/fila.
"""
from __future__ import annotations

# cluster_id (lowercase) -> capacidades
# masc/fem = lugares dentro; espera = capacidade da fila; total = soma
CLUSTER_CAPACITY: dict[str, dict] = {
    "wc-01": {"masc": 72,  "fem": 63, "espera": 81.0,  "total": 216.0,  "unisex": False},
    "wc-02": {"masc": 54,  "fem": 72, "espera": 100.8, "total": 226.8,  "unisex": False},
    "wc-03": {"masc": 54,  "fem": 48, "espera": 81.6,  "total": 183.6,  "unisex": False},
    "wc-04": {"masc": 84,  "fem": 66, "espera": 120.0, "total": 270.0,  "unisex": False},
    "wc-05": {"masc": 133, "fem": 0,  "espera": 106.4, "total": 239.4,  "unisex": True},
    "wc-06": {"masc": 208, "fem": 0,  "espera": 166.4, "total": 374.4,  "unisex": True},
    "wc-07": {"masc": 84,  "fem": 54, "espera": 110.4, "total": 248.4,  "unisex": False},
    "wc-08": {"masc": 84,  "fem": 61, "espera": 116.0, "total": 261.0,  "unisex": False},
}

ALL_CLUSTERS: list[str] = list(CLUSTER_CAPACITY.keys())
UNISEX_CLUSTERS: frozenset[str] = frozenset(
    c for c, v in CLUSTER_CAPACITY.items() if v["unisex"]
)


def capacity_inside(cluster_id: str) -> int:
    """Lugares dentro do WC (masc + fem). Denominador da ocupacao."""
    v = CLUSTER_CAPACITY.get(cluster_id.lower())
    if not v:
        return 0
    return int(v["masc"] + v["fem"])


def capacity_gender(cluster_id: str, gender: str) -> int:
    """Lugares de um genero ('M'/'F'). 0 para unissex no genero errado."""
    v = CLUSTER_CAPACITY.get(cluster_id.lower())
    if not v:
        return 0
    return int(v["masc"]) if gender == "M" else int(v["fem"])


def occupancy_pct(cluster_id: str, people_inside: float) -> float:
    """Ocupacao % = pessoas dentro / capacidade dentro, limitado a [0,100]."""
    cap = capacity_inside(cluster_id)
    if cap <= 0:
        return 0.0
    return round(min(100.0, max(0.0, people_inside / cap * 100.0)), 1)


def is_unisex(cluster_id: str) -> bool:
    return cluster_id.lower() in UNISEX_CLUSTERS
