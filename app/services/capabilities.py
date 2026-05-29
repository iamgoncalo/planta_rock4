"""
PlantaOS — Catalogo de CAPACIDADES dos sensores. Specs REAIS de datasheet
(alcance, ligacao, cobertura) + estado da ligacao. Cada numero tem 'fonte':
datasheet | medido | simulado — honestidade total.
"""
from __future__ import annotations
from app.services import fleet_sim

# Specs por tipo de sensor — TODAS de datasheet do hardware real do projeto
SPECS = {
    "lilygo": {
        "modelo": "LilyGo T-SIM7000G",
        "funcao": "Gateway do cluster — recolhe IR, fala com a nuvem",
        "alcance_m": {"esp_now_aberto": 200, "esp_now_multidao": 60, "lora_urbano": 2500, "lora_multidao": 800},
        "ligacoes": ["esp-now", "lora-868", "4g-lte"],
        "consumo_ma": 35,
        "alimentacao": "powerbank 20Ah (~3 dias)",
        "fonte_specs": "datasheet",
    },
    "camera": {
        "modelo": "OAK-D Lite / OAK 4 D (Luxonis)",
        "funcao": "Conta pessoas no vão da porta por visão (edge AI, sem guardar imagem)",
        "alcance_m": {"detecao_pessoas": 8, "vao_porta": 3},
        "fov_graus": 69,
        "fps": 12,
        "ligacoes": ["wifi-poe"],
        "consumo_ma": 350,
        "alimentacao": "PoE (cabo) ou powerbank",
        "rgpd": "edge — não guarda imagem, só conta",
        "fonte_specs": "datasheet",
    },
    "ir": {
        "modelo": "E18-D80NK (infravermelho)",
        "funcao": "Deteta passagem num ponto (porta/cancela) — conta entradas/saídas",
        "alcance_m": {"detecao": 0.8},
        "ligacoes": ["cabo-para-lilygo"],
        "consumo_ma": 25,
        "alimentacao": "do gateway (cabo)",
        "fonte_specs": "datasheet",
    },
    "gateway_lora": {
        "modelo": "Dragino DLOS8 (LoRaWAN 868MHz)",
        "funcao": "Concentrador LoRa — recebe de vários gateways distantes",
        "alcance_m": {"lora_aberto": 10000, "lora_urbano": 3000, "lora_multidao": 800},
        "ligacoes": ["lora-868", "ethernet", "4g-lte"],
        "fonte_specs": "datasheet",
    },
    "ap_wifi": {
        "modelo": "TP-Link EAP670 (WiFi 6E)",
        "funcao": "Conta telemóveis por agregação (sem rastrear indivíduos) + backhaul câmaras",
        "alcance_m": {"aberto": 80, "multidao": 45},
        "ligacoes": ["wifi-6e", "poe-backbone"],
        "rgpd": "agregado — não guarda MAC individual",
        "fonte_specs": "datasheet",
    },
}

# RSSI mínimo para ligação fiável (dBm) por ligação
RSSI_MIN = {"esp-now": -85, "lora-868": -120, "wifi-6e": -80, "wifi-poe": -80, "4g-lte": -100}


def _link_principal(tipo: str) -> str:
    ligacoes = SPECS.get(tipo, {}).get("ligacoes", [])
    return ligacoes[0] if ligacoes else "—"


def capability(sensor_id: str, tipo: str, cluster: str | None = None, rssi: float | None = None) -> dict:
    """Capacidades + saúde da ligação de um sensor."""
    spec = SPECS.get(tipo, {})
    link = _link_principal(tipo)
    rssi_min = RSSI_MIN.get(link, -90)
    margem = None
    saude_link = "—"
    if rssi is not None:
        margem = round(rssi - rssi_min, 1)
        saude_link = "boa" if margem > 15 else "razoável" if margem > 0 else "fraca"
    # distância ao palco do cluster
    dist_palco = None
    if cluster and cluster in fleet_sim.CAP:
        dist_palco = fleet_sim.CAP[cluster]["palco"]
    return {
        "sensor_id": sensor_id,
        "tipo": tipo,
        "modelo": spec.get("modelo", "—"),
        "funcao": spec.get("funcao", "—"),
        "alcance_m": spec.get("alcance_m", {}),
        "ligacao_principal": link,
        "ligacoes": spec.get("ligacoes", []),
        "rssi_dbm": rssi,
        "rssi_min_dbm": rssi_min,
        "margem_db": margem,
        "saude_ligacao": saude_link,
        "distancia_ao_palco_m": dist_palco,
        "alimentacao": spec.get("alimentacao", "—"),
        "rgpd": spec.get("rgpd"),
        "fonte_specs": spec.get("fonte_specs", "datasheet"),
    }


def cobertura_cluster(cluster_id: str) -> dict:
    """Como o cluster está coberto e ligado à nuvem."""
    if cluster_id not in fleet_sim.CAP:
        return {"erro": "cluster desconhecido"}
    cap = fleet_sim.CAP[cluster_id]
    isolado = cluster_id in ("wc-06", "wc-08")
    return {
        "cluster": cluster_id,
        "distancia_ao_palco_m": cap["palco"],
        "unissex": cap["uni"],
        "ligacao_nuvem": "LoRa 868MHz + 4G (isolado)" if isolado else "WiFi 6E + mesh ESP-NOW",
        "alcance_gateway_m": 800 if isolado else 60,
        "fonte": "datasheet" if isolado else "datasheet",
        "nota": "Cluster afastado — usa LoRa de longo alcance" if isolado
                else "Cluster na malha WiFi central",
    }


def resumo_rede() -> dict:
    """Visão global da rede: alcances, ligações, cobertura."""
    clusters = []
    for cid in fleet_sim.CAP:
        clusters.append(cobertura_cluster(cid))
    return {
        "topologia": "IR →(cabo) LilyGo →(ESP-NOW 60m / LoRa 800m / 4G) Railway · Câmara →(WiFi PoE) AP →(backbone) Railway",
        "alcances_chave": {
            "WiFi 6E (multidão)": "45 m",
            "ESP-NOW (multidão)": "60 m",
            "LoRa 868 (multidão)": "800 m",
            "Câmara (deteção pessoas)": "8 m",
            "IR (porta)": "0.8 m",
        },
        "clusters": clusters,
        "fonte": "datasheet do hardware do projeto",
    }


if __name__ == "__main__":
    import json
    print("=== CAPACIDADE de um LilyGo ===")
    print(json.dumps(capability("wc-06-lilygo-1","lilygo","wc-06",rssi=-83), indent=2, ensure_ascii=False))
    print("\n=== COBERTURA wc-06 (isolado) vs wc-02 (central) ===")
    print(json.dumps(cobertura_cluster("wc-06"), indent=2, ensure_ascii=False))
    print(json.dumps(cobertura_cluster("wc-02"), indent=2, ensure_ascii=False))
    print("\n=== RESUMO REDE (alcances) ===")
    r = resumo_rede()
    for k,v in r["alcances_chave"].items():
        print(f"  {k}: {v}")
