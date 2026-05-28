"""
clusters_geo.py — FONTE DE VERDADE ÚNICA da geometria dos 8 clusters de WC.

>>> ESTE É O ÚNICO SÍTIO ONDE SE EDITAM COORDENADAS. <<<
Toda a plataforma (twin, chat2, sensores, routing) lê daqui via /api/v1/clusters/geo.

Sistema de coordenadas:
  - Métrico (e_m, n_m): origem (0,0) = canto SW = WC-08. Norte para cima.
    Eixo E = Este (metros), eixo N = Norte (metros). bbox 0..298.5 (E) × 0..327.3 (N).
    Fonte: malha verificada §GRID (planta geral R08, 24/03/2026).
  - GPS: âncora única do recinto. (0,0) métrico corresponde a ANCHOR_GPS.
    Cada cluster recebe lat/lon derivado dos metros (não inventado por cluster).

Para mudar a localização do recinto no futuro: edita ANCHOR_GPS.
Para corrigir um cluster: edita só o seu (e_m, n_m) aqui.
"""
from __future__ import annotations
import math

# Âncora GPS do ponto métrico (0,0) = WC-08 (canto SW do recinto).
# Centro do recinto fica ~ (149, 164) m -> ~38.7828, -9.0928 (verificado).
ANCHOR_GPS = {"lat": 38.78145, "lon": -9.09430}

# metros -> graus (à latitude do recinto)
_M_PER_DEG_LAT = 111_320.0
_M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(ANCHOR_GPS["lat"]))

# Os 8 clusters. type: "MF" (masc+fem separados) | "UNI" (unissex, um valor).
# e_m/n_m em metros (malha §GRID). cap_m/cap_f para MF; cap para UNI.
CLUSTERS_GEO = [
    {"id": "WC-01", "e_m": 215.2, "n_m": 327.3, "type": "MF",  "desc": "V34 · junto ao Parque P1",      "cap_m": 72, "cap_f": 63},
    {"id": "WC-02", "e_m": 256.9, "n_m": 286.1, "type": "MF",  "desc": "V35 · feminino dominante",      "cap_m": 54, "cap_f": 72},
    {"id": "WC-03", "e_m": 268.2, "n_m": 194.8, "type": "MF",  "desc": "S36 · entrada principal",       "cap_m": 54, "cap_f": 48},
    {"id": "WC-04", "e_m": 298.5, "n_m": 288.3, "type": "MF",  "desc": "S37 · cota +20 m (ADA)",        "cap_m": 84, "cap_f": 66},
    {"id": "WC-05", "e_m": 274.2, "n_m": 238.2, "type": "UNI", "desc": "M38 · só entrada",              "cap": 133},
    {"id": "WC-06", "e_m": 60.7,  "n_m": 82.4,  "type": "UNI", "desc": "W39/S39 · maior cluster",       "cap": 208},
    {"id": "WC-07", "e_m": 228.2, "n_m": 148.1, "type": "MF",  "desc": "M40 · cacifos",                 "cap_m": 84, "cap_f": 54},
    {"id": "WC-08", "e_m": 0.0,   "n_m": 0.0,   "type": "MF",  "desc": "V41 · produção",                "cap_m": 84, "cap_f": 61},
]

# Pontos de interesse para enquadramento do mapa (mesmos metros).
LANDMARKS = [
    {"id": "ENTRADA",      "label": "Entrada Principal", "e_m": 290.0, "n_m": 175.0, "kind": "entrance"},
    {"id": "PALCO_MUNDO",  "label": "Palco Mundo",       "e_m": 70.0,  "n_m": 120.0, "kind": "stage"},
    {"id": "MUSIC_VALLEY", "label": "Music Valley",      "e_m": 30.0,  "n_m": 60.0,  "kind": "stage"},
    {"id": "SUPER_BOCK",   "label": "Super Bock",        "e_m": 120.0, "n_m": 70.0,  "kind": "stage"},
]

# bbox métrico (para o motor de escala no frontend)
SPAN_E = max(c["e_m"] for c in CLUSTERS_GEO)  # 298.5
SPAN_N = max(c["n_m"] for c in CLUSTERS_GEO)  # 327.3


def _gps_from_metres(e_m: float, n_m: float) -> dict:
    """Deriva lat/lon a partir dos metros, ancorado em ANCHOR_GPS."""
    return {
        "lat": round(ANCHOR_GPS["lat"] + n_m / _M_PER_DEG_LAT, 6),
        "lon": round(ANCHOR_GPS["lon"] + e_m / _M_PER_DEG_LON, 6),
    }


def _capacity(c: dict) -> int:
    if c["type"] == "UNI":
        return int(c.get("cap", 0))
    return int(c.get("cap_m", 0)) + int(c.get("cap_f", 0))


def build_geo_payload() -> dict:
    """Payload servido por /api/v1/clusters/geo — a fonte de verdade para o frontend."""
    clusters = []
    for c in CLUSTERS_GEO:
        gps = _gps_from_metres(c["e_m"], c["n_m"])
        clusters.append({
            "id": c["id"],
            "e_m": c["e_m"],
            "n_m": c["n_m"],
            "gps_lat": gps["lat"],
            "gps_lon": gps["lon"],
            "type": c["type"],
            "unisex": c["type"] == "UNI",
            "desc": c["desc"],
            "cap_m": c.get("cap_m"),
            "cap_f": c.get("cap_f"),
            "cap": c.get("cap"),
            "capacity_total": _capacity(c),
        })
    return {
        "anchor_gps": ANCHOR_GPS,
        "span_e_m": SPAN_E,
        "span_n_m": SPAN_N,
        "clusters": clusters,
        "landmarks": LANDMARKS,
        "total_clusters": len(clusters),
    }


def distance_m(id_a: str, id_b: str) -> float:
    """Distância euclidiana real (metros) entre dois clusters."""
    m = {c["id"]: c for c in CLUSTERS_GEO}
    a, b = m[id_a], m[id_b]
    return round(math.hypot(a["e_m"] - b["e_m"], a["n_m"] - b["n_m"]), 1)
