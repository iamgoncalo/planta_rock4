"""
DB-agnostic seeds — funciona em SQLite OU PostgreSQL.
Arquitetura REAL RiR2026 (U4):

  34 LilyGo TTGO LoRa32 V2.1:
    - 6 clusters M/F × 5 = 30 (LLH/LRH/LLW/LRW/LC)
    - 2 clusters UNI × 2  =  4 (UNI-A/UNI-B)
   2 Gateways LoRa Dragino DLOS8 (Norte + Sul)
   6 Câmaras Luxonis OAK-D Lite (1 por cluster M/F)
   8 Contagens Prosegur (1 por cluster)
  ──
  50 total
"""
from __future__ import annotations
import logging
from sqlalchemy import select, func

from app.clusters_geo import CLUSTER_GPS, CLUSTERS_GEO as _CLUSTERS_GEO, GATEWAY_NORTH_GPS, GATEWAY_SOUTH_GPS

logger = logging.getLogger(__name__)

_MF_CLUSTERS  = [c for c in _CLUSTERS_GEO if c["type"] == "MF"]
_UNI_CLUSTERS = [c for c in _CLUSTERS_GEO if c["type"] == "UNI"]


def _lid(cluster_id: str, role: str) -> str:
    """lilygo_wc01_h_ll"""
    return f"lilygo_{cluster_id.lower().replace('-', '')}_{role}"


def _sensor_seed_rows() -> list[dict]:
    rows: list[dict] = []

    for c in _MF_CLUSTERS:
        cid = c["id"]
        lat, lon = CLUSTER_GPS[cid]
        cid_l = cid.lower()

        # 5 LilyGo por cluster M/F
        specs = [
            (_lid(cid, "h_ll"),   "LL", "m", True,  f"{cid} MASC LL — porta esquerda"),
            (_lid(cid, "h_lr"),   "LR", "m", True,  f"{cid} MASC LR — porta direita"),
            (_lid(cid, "w_ll"),   "LL", "f", True,  f"{cid} FEM LL — porta esquerda"),
            (_lid(cid, "w_lr"),   "LR", "f", True,  f"{cid} FEM LR — porta direita"),
            (_lid(cid, "center"), "C",  "m", False, f"{cid} LC — corredor central, sem IR"),
        ]
        for sid, porta, secao, usar_ir, desc in specs:
            rows.append({
                "id": sid,
                "cluster_id": cid_l,
                "type": "lilygo",
                "model": "LilyGo TTGO LoRa32 V2.1 (ESP32-PICO-D4)",
                "protocol": "wifi+lorawan",
                "location_desc": desc,
                "gps_lat": lat,
                "gps_lon": lon,
                "height_cm": 280,
                "has_battery": True,
                "battery_mah": 10_000,
                "powered_by": "LiPo 10Ah",
                "ip_rating": "IP54",
                "fusion_weight": 0.30,
                "firmware": "plantaos-rir2026-v1",
                "notes": f"porta={porta or 'C'} secao={secao} usar_ir={'sim' if usar_ir else 'nao'} IR_A=GPIO36(VP) IR_B=IO33 debounce=-10000",
                "critical_note": "GPIO36=IR_A exterior, IO33=IR_B interior" if usar_ir else None,
                "cost_eur": 45.0,
                "is_active": True,
            })

        # 1 Luxonis OAK-D Lite por cluster M/F
        rows.append({
            "id": f"luxonis_{cid_l.replace('-', '')}",
            "cluster_id": cid_l,
            "type": "luxonis",
            "model": "Luxonis OAK-D Lite",
            "protocol": "usb3",
            "location_desc": f"{cid} — câmara edge ML, montada no tecto",
            "gps_lat": lat,
            "gps_lon": lon,
            "height_cm": 280,
            "has_battery": False,
            "powered_by": "USB-C 5V (edge node)",
            "ip_rating": "IP20",
            "fusion_weight": 0.20,
            "firmware": "oak-d-lite-v2.8",
            "notes": "fonte=luxonis → FusionInput.luxonis_count (peso cam 0.20)",
            "cost_eur": 149.0,
            "is_active": True,
        })

    for c in _UNI_CLUSTERS:
        cid = c["id"]
        lat, lon = CLUSTER_GPS[cid]
        cid_l = cid.lower()

        # 2 LilyGo por cluster UNI
        for tag in ("a", "b"):
            rows.append({
                "id": _lid(cid, f"uni_{tag}"),
                "cluster_id": cid_l,
                "type": "lilygo",
                "model": "LilyGo TTGO LoRa32 V2.1 (ESP32-PICO-D4)",
                "protocol": "wifi+lorawan",
                "location_desc": f"{cid} UNI-{tag.upper()} — sem IR (unissexo)",
                "gps_lat": lat,
                "gps_lon": lon,
                "height_cm": 280,
                "has_battery": True,
                "battery_mah": 10_000,
                "powered_by": "LiPo 10Ah",
                "ip_rating": "IP54",
                "fusion_weight": 0.30,
                "firmware": "plantaos-rir2026-v1",
                "notes": "secao=u usar_ir=nao (unissexo — sem sensor IR)",
                "cost_eur": 45.0,
                "is_active": True,
            })

    # Prosegur por cluster (todos os 8)
    for c in _CLUSTERS_GEO:
        cid = c["id"]
        lat, lon = CLUSTER_GPS[cid]
        cid_l = cid.lower()
        rows.append({
            "id": f"prosegur_{cid_l.replace('-', '')}",
            "cluster_id": cid_l,
            "type": "prosegur",
            "model": "Prosegur contador manual",
            "protocol": "manual",
            "location_desc": f"{cid} — contagem manual Prosegur (segurança)",
            "gps_lat": lat,
            "gps_lon": lon,
            "has_battery": False,
            "powered_by": "manual",
            "fusion_weight": 0.0,
            "notes": "fonte=prosegur → FusionInput.contagem_prosegur (âncora, não entra no sum)",
            "cost_eur": 0.0,
            "is_active": True,
        })

    # 2 Gateways LoRa Dragino DLOS8
    rows.append({
        "id": "gw_north",
        "cluster_id": None,
        "type": "lorawan_gateway",
        "model": "Dragino DLOS8",
        "protocol": "lorawan",
        "location_desc": "Gateway LoRa Norte — cobre WC-01, WC-02, WC-03, WC-04",
        "gps_lat": GATEWAY_NORTH_GPS[0],
        "gps_lon": GATEWAY_NORTH_GPS[1],
        "has_battery": False,
        "powered_by": "PoE",
        "ip_rating": "IP67",
        "coverage_radius_m": 2000,
        "cost_eur": 280.0,
        "is_active": True,
    })
    rows.append({
        "id": "gw_south",
        "cluster_id": None,
        "type": "lorawan_gateway",
        "model": "Dragino DLOS8",
        "protocol": "lorawan",
        "location_desc": "Gateway LoRa Sul — cobre WC-05, WC-06, WC-07, WC-08",
        "gps_lat": GATEWAY_SOUTH_GPS[0],
        "gps_lon": GATEWAY_SOUTH_GPS[1],
        "has_battery": False,
        "powered_by": "PoE",
        "ip_rating": "IP67",
        "coverage_radius_m": 2000,
        "cost_eur": 280.0,
        "is_active": True,
    })

    return rows


async def seed_sensors_if_empty(session_factory) -> None:
    """Se a tabela sensors estiver vazia, insere 50 linhas (34 LilyGo + 6 Lux + 8 Pro + 2 GW)."""
    from app.models.db.sensors import Sensor, SensorHealth

    async with session_factory() as session:
        result = await session.execute(select(func.count()).select_from(Sensor))
        existing = result.scalar() or 0
        if existing > 0:
            logger.info(f"Seed skip: {existing} sensors já existem")
            return

        rows = _sensor_seed_rows()
        valid_cols = {c.name for c in Sensor.__table__.columns}

        for r in rows:
            kwargs = {k: v for k, v in r.items() if k in valid_cols}
            session.add(Sensor(**kwargs))

        await session.flush()

        health_cols = {c.name for c in SensorHealth.__table__.columns}
        for r in rows:
            h = {"sensor_id": r["id"]}
            if "status" in health_cols:
                h["status"] = "unknown"
            if "events_today" in health_cols:
                h["events_today"] = 0
            session.add(SensorHealth(**h))

        await session.commit()
        logger.info(f"Seed RiR2026: {len(rows)} sensors inseridos (34 LilyGo + 6 Lux + 8 Pro + 2 GW)")
