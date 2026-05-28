"""
PlantaOS — Ingestao de dados REAIS dos sensores (LilyGo + IR + ML).
POST /api/v1/ingest   (auth: header X-Ops-Secret)

Formato canonico (= envio SCOR):
  { "cluster_id":"wc-01", "ts":1634712287000,
    "params": { "telemoveis_detectados":34, "pessoas_estimadas":25,
      "homens":12, "mulheres":13, "entradas_ir":22, "saidas_ir":44,
      "ocupacao_instantanea":33, "contagem_prosegur":31,
      "confianca_cruzada":0.8, "estado_sensor":"okay" } }

wc-05 / wc-06 sao UNISSEX -> homens/mulheres devem ser null.
Aceita payload fundido (com pessoas_estimadas) OU cru (so fontes); a Fase 2
fara a fusao inteligente. Por agora, guarda e expoe o que recebe.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

from app.config import get_settings
from app.services import ingest_store
from app.clusters_capacity import ALL_CLUSTERS, is_unisex, occupancy_pct

router = APIRouter(prefix="/api/v1", tags=["ingest"])


class IngestParams(BaseModel):
    telemoveis_detectados: Optional[int] = None
    pessoas_estimadas: Optional[float] = None
    homens: Optional[int] = None
    mulheres: Optional[int] = None
    entradas_ir: Optional[int] = None
    saidas_ir: Optional[int] = None
    ocupacao_instantanea: Optional[float] = None
    contagem_prosegur: Optional[int] = None
    confianca_cruzada: Optional[float] = None
    estado_sensor: Optional[str] = "okay"

    class Config:
        extra = "allow"  # permite fontes cruas extra (ml, etc.) sem rejeitar


class IngestBody(BaseModel):
    cluster_id: str
    ts: Optional[int] = None
    params: IngestParams


def _check_auth(secret: Optional[str]) -> None:
    expected = get_settings().ops_secret
    if not expected or expected == "change-me":
        # Em dev sem segredo definido, nao bloqueia (mas avisa nos logs).
        return
    if secret != expected:
        raise HTTPException(status_code=401, detail="invalid ops secret")


@router.post("/ingest")
async def ingest(body: IngestBody, x_ops_secret: Optional[str] = Header(default=None)):
    _check_auth(x_ops_secret)

    cid = body.cluster_id.lower()
    if cid not in ALL_CLUSTERS:
        raise HTTPException(status_code=422, detail=f"cluster_id desconhecido: {body.cluster_id!r}")

    p = body.params.model_dump()

    # Regra unissex: wc-05/wc-06 nao tem split por genero.
    if is_unisex(cid):
        p["homens"] = None
        p["mulheres"] = None

    # Se nao veio ocupacao, mas veio pessoas_estimadas, deriva da capacidade real.
    if p.get("ocupacao_instantanea") is None and p.get("pessoas_estimadas") is not None:
        p["ocupacao_instantanea"] = occupancy_pct(cid, float(p["pessoas_estimadas"]))

    ingest_store.put(cid, p, body.ts)
    return {"ok": True, "cluster_id": cid, "stored_ts": body.ts, "unisex": is_unisex(cid)}


@router.get("/ingest/status")
async def ingest_status():
    """Estado de ingestao por cluster: fonte (real/stale/none) + idade."""
    ttl = float(get_settings().real_data_ttl_s)
    snap = ingest_store.snapshot(ttl)
    # garante os 8 clusters na resposta
    out = {}
    for cid in ALL_CLUSTERS:
        out[cid] = snap.get(cid, {"data_source": "none", "age_s": None, "ts_device": None})
    return {"data_ttl_s": ttl, "clusters": out}
