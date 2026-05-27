from __future__ import annotations
from fastapi import APIRouter
from app.models.sections import SECTION_IDS, UNISEX_SECTIONS
from app.services.state import get_live_payload

router = APIRouter(prefix="/api/v1", tags=["clusters"])

# The 8 clusters with their member sections
_CLUSTER_MAP: dict[str, list[str]] = {
    "WC-01": ["WC-01_M", "WC-01_F"],
    "WC-02": ["WC-02_M", "WC-02_F"],
    "WC-03": ["WC-03_M", "WC-03_F"],
    "WC-04": ["WC-04_M", "WC-04_F"],
    "WC-05": ["WC-05"],
    "WC-06": ["WC-06"],
    "WC-07": ["WC-07_M", "WC-07_F"],
    "WC-08": ["WC-08_M", "WC-08_F"],
}


@router.get("/clusters")
async def list_clusters():
    """Return summary for all 8 WC clusters with their section states."""
    payload = get_live_payload()
    section_map = {s.section_id: s for s in payload.sections}

    clusters = []
    for cluster_id, member_ids in _CLUSTER_MAP.items():
        members = [section_map[sid] for sid in member_ids if sid in section_map]
        avg_occ = sum(m.ocupacao_pct for m in members) / len(members) if members else 0.0
        total_fila = sum(m.fila_atual for m in members)
        any_critical = any(m.status == "critical" for m in members)
        any_offline = any(m.status == "offline" for m in members)
        cluster_status = "critical" if any_critical else ("offline" if any_offline else "normal")
        unisex = cluster_id in UNISEX_SECTIONS or cluster_id in {"WC-05", "WC-06"}

        clusters.append({
            "cluster_id": cluster_id,
            "unisex": unisex,
            "sections": [m.model_dump() for m in members],
            "summary": {
                "avg_ocupacao_pct": round(avg_occ, 1),
                "total_fila": total_fila,
                "status": cluster_status,
                "simulated": any(m.simulated for m in members),
            },
        })

    return {"clusters": clusters, "total_clusters": len(clusters)}
