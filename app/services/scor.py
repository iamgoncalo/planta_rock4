"""SCOR telemetry publisher — dry-run safe.

SCOR payload fields (exactly): cluster_id, fila_actual, tempo_espera_min,
fluxo_entrada_pmin, ocupacao_pct.  No GPS. No CO2. No temperature. No humidity.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

from app.models.sections import SECTION_IDS

logger = logging.getLogger(__name__)

# Forbidden cluster_id values — gendered variants of unisex sections
_FORBIDDEN_CLUSTER_IDS: frozenset[str] = frozenset({
    "WC-05_M", "WC-05_F",
    "WC-06_M", "WC-06_F",
})

# Fields that must never appear in SCOR payloads
_FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    "lat", "lon", "latitude", "longitude", "gps_lat", "gps_lon",
    "co2", "co2_ppm", "temperature", "temperatura", "humidity", "humidade",
    "mac", "mac_address", "device_mac",
})

# The 14 allowed section IDs map to SCOR cluster_ids
# (WC-05 and WC-06 are unisex; all others map to their cluster prefix)
_SECTION_TO_CLUSTER: dict[str, str] = {
    sid: (sid.split("_")[0] if "_" in sid else sid)
    for sid in SECTION_IDS
}


def _strip_forbidden(entry: dict[str, Any]) -> dict[str, Any]:
    """Return entry with only the 5 allowed SCOR fields, stripping any forbidden fields."""
    allowed_keys = {
        "cluster_id", "fila_actual", "tempo_espera_min",
        "fluxo_entrada_pmin", "ocupacao_pct",
    }
    return {k: v for k, v in entry.items() if k in allowed_keys}


def _validate_cluster_id(cluster_id: str) -> None:
    if cluster_id in _FORBIDDEN_CLUSTER_IDS:
        raise ValueError(
            f"Forbidden cluster_id '{cluster_id}': "
            "WC-05 and WC-06 are unisex — gendered variants must never be sent to SCOR."
        )


def build_scor_entries(sections: list[Any]) -> list[dict[str, Any]]:
    """Convert SectionState list into 14 SCOR-compliant payload entries.

    Each entry has exactly: cluster_id, fila_actual, tempo_espera_min,
    fluxo_entrada_pmin, ocupacao_pct.
    No GPS. No CO2. No temperature. No humidity.
    """
    if len(sections) != 14:
        raise ValueError(f"Expected exactly 14 sections, got {len(sections)}")

    entries = []
    for s in sections:
        # Derive cluster_id from section_id
        section_id = s.section_id if hasattr(s, "section_id") else s["section_id"]
        cluster_id = _SECTION_TO_CLUSTER.get(section_id, section_id)

        _validate_cluster_id(cluster_id)

        # Build entry with exactly 5 SCOR fields — no GPS, no CO2
        entry = {
            "cluster_id": cluster_id,
            "fila_actual": int(s.fila_atual if hasattr(s, "fila_atual") else s["fila_atual"]),
            "tempo_espera_min": float(s.tempo_espera_min if hasattr(s, "tempo_espera_min") else s["tempo_espera_min"]),
            "fluxo_entrada_pmin": float(s.fluxo_entrada_pmin if hasattr(s, "fluxo_entrada_pmin") else s["fluxo_entrada_pmin"]),
            "ocupacao_pct": float(s.ocupacao_pct if hasattr(s, "ocupacao_pct") else s["ocupacao_pct"]),
        }
        # Strip any accidental forbidden fields (defence-in-depth)
        entry = _strip_forbidden(entry)
        entries.append(entry)

    if len(entries) != 14:
        raise ValueError(f"Post-build entry count mismatch: expected 14, got {len(entries)}")

    return entries


async def publish_scor_kpis(kpis: Any, dry_run: bool = True) -> dict[str, Any]:
    """Post KPIs to SCOR. dry_run=True → log only, no HTTP."""
    token = os.environ.get("SCOR_TOKEN_KPI", "")
    base_url = os.environ.get("SCOR_BASE_URL", "")

    kpis_dict = kpis.model_dump() if hasattr(kpis, "model_dump") else dict(kpis)
    # Strip forbidden fields from KPI payload too
    kpis_dict = {k: v for k, v in kpis_dict.items() if k not in _FORBIDDEN_FIELDS}

    if dry_run:
        logger.info("[SCOR KPI DRY-RUN] Would POST to %s/kpis — payload: %s", base_url, kpis_dict)
        return {"status": "dry_run", "payload": kpis_dict}

    if not token or not base_url:
        logger.warning("[SCOR KPI] Missing SCOR_TOKEN_KPI or SCOR_BASE_URL — skipping")
        return {"status": "skipped_no_config"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{base_url}/kpis",
            json=kpis_dict,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return {"status": "sent", "http_status": resp.status_code}


async def publish_scor_sections(sections: list[Any], dry_run: bool = True) -> dict[str, Any]:
    """Post 14-section telemetry to SCOR.

    Each entry: cluster_id, fila_actual, tempo_espera_min,
    fluxo_entrada_pmin, ocupacao_pct ONLY.
    No GPS. No CO2. Exactly 14 rows per call.
    Never sends WC-05_M, WC-05_F, WC-06_M, WC-06_F.
    Tokens read from env: SCOR_TOKEN_KPI, SCOR_TOKEN_CLUSTER, SCOR_BASE_URL.
    """
    token = os.environ.get("SCOR_TOKEN_CLUSTER", "")
    base_url = os.environ.get("SCOR_BASE_URL", "")

    entries = build_scor_entries(sections)

    # Final guard: confirm no forbidden fields leaked through
    for entry in entries:
        for forbidden in _FORBIDDEN_FIELDS:
            if forbidden in entry:
                raise RuntimeError(
                    f"Forbidden field '{forbidden}' detected in SCOR payload — aborting."
                )

    # Confirm no forbidden cluster_ids
    for entry in entries:
        _validate_cluster_id(entry["cluster_id"])

    if dry_run:
        logger.info(
            "[SCOR SECTIONS DRY-RUN] Would POST %d entries to %s/sections. Sample: %s",
            len(entries),
            base_url,
            entries[0] if entries else {},
        )
        return {
            "status": "dry_run",
            "sections_sent": len(entries),
            "entries": entries,
        }

    if not token or not base_url:
        logger.warning("[SCOR SECTIONS] Missing SCOR_TOKEN_CLUSTER or SCOR_BASE_URL — skipping")
        return {"status": "skipped_no_config", "sections_sent": 0}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{base_url}/sections",
            json={"sections": entries, "ts": time.time()},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return {
            "status": "sent",
            "http_status": resp.status_code,
            "sections_sent": len(entries),
        }
