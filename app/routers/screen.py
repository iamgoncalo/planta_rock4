"""
PlantaOS · Screen copy router
================================
GET /api/v1/screen/copy — frases contextuais por secção, geradas pelo motor
de copy que compara todos os clusters em conjunto (não frases fixas).
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Response

from app.copy_engine import build_copy, ClusterSnapshot, SectionInput
from app.services.state import get_live_payload

router = APIRouter(prefix="/api/v1/screen", tags=["screen"])

_UNISEX_IDS = frozenset({"wc-05", "wc-06"})


def _state_to_clusters() -> list[ClusterSnapshot]:
    payload = get_live_payload()
    clusters_dict: dict[str, list[SectionInput]] = {}

    for sec in payload.sections:
        sid = sec.section_id  # "WC-01_M" | "WC-01_F" | "WC-05"
        parts = sid.upper().split("_")
        cluster_id = parts[0].lower()              # "wc-01"
        seccao = parts[1].lower() if len(parts) == 2 else "u"  # "m"/"f"/"u"
        section_id = f"{cluster_id}_{seccao}"      # "wc-01_m"
        is_unissex = cluster_id in _UNISEX_IDS

        si = SectionInput(
            section_id=section_id,
            cluster_id=cluster_id,
            seccao=seccao,
            ocupacao_pct=sec.ocupacao_pct,
            fila=sec.fila_atual,
            espera_min=sec.tempo_espera_min,
            fluxo_pmin=sec.fluxo_entrada_pmin,
            confianca=sec.confianca,
            live=not sec.stale,
            is_unissex=is_unissex,
        )
        clusters_dict.setdefault(cluster_id, []).append(si)

    return [ClusterSnapshot(cid, secs) for cid, secs in clusters_dict.items()]


@router.get("/copy")
async def screen_copy(response: Response) -> dict[str, Any]:
    """Frases contextuais por secção — motor compara os 8 clusters em conjunto.

    Resposta: dict de section_id → {pt, en, tom}.
    """
    response.headers["Cache-Control"] = "public, max-age=5, s-maxage=5"
    clusters = _state_to_clusters()
    now_ms = int(time.time() * 1000)
    copy = build_copy(clusters, now_ms)
    return {
        sid: {"pt": sc.pt, "en": sc.en, "tom": sc.tom}
        for sid, sc in copy.items()
    }
