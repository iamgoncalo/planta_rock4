"""
PlantaOS — Registo da frota de sensores (FONTE DE VERDADE UNICA).
Filosofia: LilyGo em todos (coração, powerbank, sem fios). Camara onde existe
(fonte rica preferida). IR ao minimo, opcional e removivel por cluster.
Tudo configuravel: editar AQUI adiciona/remove sensores e a fusao adapta-se.

Tipos: lilygo | camera | ir | gateway_lora | ap_wifi
Camaras reais: OAK-D Lite (wc-04) + OAK 4 D (wc-06). Restantes: planeadas.
"""
from __future__ import annotations
from typing import Literal, Optional

SensorType = Literal["lilygo", "camera", "ir", "gateway_lora", "ap_wifi"]
PowerType = Literal["powerbank", "electric", "poe", "mains"]
LinkType = Literal["wifi", "wifi+espnow", "lora+sim", "lora+4g", "ethernet", "wired"]
Status = Literal["online", "degraded", "offline", "maintenance", "planned", "unknown"]

# Capacidades oficiais (= clusters_capacity). Origem unica da ocupacao.
CLUSTER_CAP = {
    "wc-01": {"masc": 72,  "fem": 63, "espera": 81.0,  "unisex": False},
    "wc-02": {"masc": 54,  "fem": 72, "espera": 100.8, "unisex": False},
    "wc-03": {"masc": 54,  "fem": 48, "espera": 81.6,  "unisex": False},
    "wc-04": {"masc": 84,  "fem": 66, "espera": 120.0, "unisex": False},
    "wc-05": {"masc": 133, "fem": 0,  "espera": 106.4, "unisex": True},
    "wc-06": {"masc": 208, "fem": 0,  "espera": 166.4, "unisex": True},
    "wc-07": {"masc": 84,  "fem": 54, "espera": 110.4, "unisex": False},
    "wc-08": {"masc": 84,  "fem": 61, "espera": 116.0, "unisex": False},
}

# Clusters isolados (fora do alcance mesh WiFi — confirmado por GPS)
ISOLATED = {"wc-06", "wc-08"}

# Camaras reais e o seu modelo. Os outros clusters: camara "planeada".
REAL_CAMERAS = {
    "wc-06": "OAK 4 D",
    "wc-04": "OAK-D Lite",
}


def _link_for(cluster_id: str) -> LinkType:
    return "lora+sim" if cluster_id in ISOLATED else "wifi+espnow"


def _power_profile(sensor_type: str) -> dict:
    """Perfil de consumo para estimativa de bateria (Anker 20Ah ~17000mAh util)."""
    # mA medio por modo
    profiles = {
        "lilygo":  {"mode": "deep-sleep-60s", "ma": 35,  "battery": "powerbank"},
        "camera":  {"mode": "duty-25%",       "ma": 200, "battery": "powerbank"},
        "ir":      {"mode": "n/a",            "ma": 0,   "battery": "electric"},
        "gateway_lora": {"mode": "always-on", "ma": 0,   "battery": "mains"},
        "ap_wifi": {"mode": "always-on",      "ma": 0,   "battery": "poe"},
    }
    return profiles.get(sensor_type, {"mode": "?", "ma": 0, "battery": "unknown"})


def build_fleet() -> list[dict]:
    """Constroi o inventario completo da frota. Cada sensor e um dict."""
    fleet: list[dict] = []

    for cid, cap in CLUSTER_CAP.items():
        n = cid[-2:]
        unisex = cap["unisex"]
        cap_inside = cap["masc"] + cap["fem"]
        big = cap_inside > 140 or cap["espera"] > 110

        # 1) LilyGo — sempre. Clusters grandes -> 2.
        n_lily = 2 if big else 1
        for i in range(1, n_lily + 1):
            fleet.append({
                "id": f"{cid}-lilygo-{i}",
                "tipo": "lilygo",
                "cluster": cid,
                "role": "gateway" if i == 1 else "node",
                "power": "powerbank",
                "power_profile": _power_profile("lilygo"),
                "link": _link_for(cid),
                "status": "planned",  # ate ligar
                "fonte_fusao": "wifi",  # contribui via WiFi sniffing
            })

        # 2) Camara — real nos 2 criticos, planeada nos restantes.
        modelo = REAL_CAMERAS.get(cid)
        fleet.append({
            "id": f"{cid}-cam-1",
            "tipo": "camera",
            "cluster": cid,
            "modelo": modelo or "ESP32-CAM (planeada)",
            "real": modelo is not None,
            "power": "powerbank",
            "power_profile": _power_profile("camera"),
            "link": "wifi",
            "status": "planned",
            "fonte_fusao": "camera",  # contagem de cabecas + H/M
        })

        # 3) IR — minimo, so nos M/F (unissex nao tem porta). 4 por porta.
        if not unisex:
            for porta in ["M", "F"]:
                for i in range(1, 5):
                    fleet.append({
                        "id": f"{cid}-ir-{porta.lower()}-{i}",
                        "tipo": "ir",
                        "cluster": cid,
                        "porta": porta,
                        "power": "electric",
                        "power_profile": _power_profile("ir"),
                        "link": "wired",  # ao LilyGo do cluster
                        "parent": f"{cid}-lilygo-1",
                        "status": "planned",
                        "fonte_fusao": "ir",  # direcao entrada/saida
                    })

    # 4) Gateways LoRa (2) — para os clusters isolados.
    for i in range(1, 3):
        fleet.append({
            "id": f"gw-lora-{i}",
            "tipo": "gateway_lora",
            "cluster": None,
            "serves": sorted(ISOLATED),
            "power": "mains",
            "power_profile": _power_profile("gateway_lora"),
            "link": "lora+4g",
            "status": "planned",
        })

    # 5) APs WiFi 6E (1 por cluster).
    for cid in CLUSTER_CAP:
        fleet.append({
            "id": f"ap-wifi-{cid[-2:]}",
            "tipo": "ap_wifi",
            "cluster": cid,
            "power": "poe",
            "power_profile": _power_profile("ap_wifi"),
            "link": "ethernet",
            "status": "planned",
        })

    return fleet


def fleet_summary(fleet: list[dict]) -> dict:
    """Contagens por tipo + por cluster."""
    by_type: dict[str, int] = {}
    by_cluster: dict[str, dict] = {}
    for s in fleet:
        by_type[s["tipo"]] = by_type.get(s["tipo"], 0) + 1
        c = s["cluster"]
        if c:
            by_cluster.setdefault(c, {})
            by_cluster[c][s["tipo"]] = by_cluster[c].get(s["tipo"], 0) + 1
    return {"total": len(fleet), "by_type": by_type, "by_cluster": by_cluster}


def capacity_inside(cluster_id: str) -> int:
    c = CLUSTER_CAP.get(cluster_id.lower())
    return int(c["masc"] + c["fem"]) if c else 0


# Fusao: que fontes existem por cluster (para os pesos adaptarem)
def fusion_sources(cluster_id: str, fleet: list[dict]) -> list[str]:
    """Que tipos de fonte de fusao o cluster tem (ir/wifi/camera)."""
    srcs = set()
    for s in fleet:
        if s.get("cluster") == cluster_id and s.get("fonte_fusao"):
            srcs.add(s["fonte_fusao"])
    return sorted(srcs)


if __name__ == "__main__":
    f = build_fleet()
    s = fleet_summary(f)
    print("TOTAL:", s["total"])
    print("Por tipo:", s["by_type"])
    print()
    for cid in CLUSTER_CAP:
        print(f"{cid}: {s['by_cluster'].get(cid, {})} | fontes fusao: {fusion_sources(cid, f)} | cap dentro: {capacity_inside(cid)}")
    print()
    print("Camaras reais:")
    for s2 in f:
        if s2["tipo"] == "camera" and s2.get("real"):
            print(f"  {s2['id']}: {s2['modelo']}")
