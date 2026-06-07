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

import time as _time
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

from app.config import get_settings
from app.services import ingest_store
from app.clusters_capacity import ALL_CLUSTERS, is_unisex, occupancy_pct
from app.sensors_topology import USAR_IR

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


def _run_fusion(cid: str, params: dict, ts_ms: int) -> None:
    """Constroi FusionInput por seccao e chama fuse_section (§3.1-3.2)."""
    try:
        from app.fusion import FusionInput, fuse_section

        usar_ir = USAR_IR.get(cid, True)
        estado = params.get("estado_sensor", "ok")
        prosegur = params.get("contagem_prosegur")
        entradas = params.get("entradas_ir")
        saidas = params.get("saidas_ir")

        if is_unisex(cid):
            fuse_section(FusionInput(
                section_id=cid,
                ts_ms=ts_ms,
                entradas_ir=entradas,
                saidas_ir=saidas,
                pessoas_estimadas=params.get("pessoas_estimadas"),
                contagem_prosegur=prosegur,
                estado_sensor=estado,
                usar_ir=usar_ir,
            ))
        else:
            homens = params.get("homens")
            mulheres = params.get("mulheres")
            pessoas = params.get("pessoas_estimadas")
            for gender, pessoas_g in (("m", homens), ("f", mulheres)):
                wifi_est = (
                    float(pessoas_g) if pessoas_g is not None
                    else (float(pessoas) / 2.0 if pessoas is not None else None)
                )
                fuse_section(FusionInput(
                    section_id=f"{cid}_{gender}",
                    ts_ms=ts_ms,
                    entradas_ir=None,   # IR cluster-level; sem split por genero
                    saidas_ir=None,
                    pessoas_estimadas=wifi_est,
                    contagem_prosegur=prosegur,
                    estado_sensor=estado,
                    usar_ir=False,      # sem IR seccional disponivel
                ))
    except Exception:
        pass   # fusao nao pode parar a ingestao


@router.post("/ingest")
async def ingest(body: IngestBody, x_ops_secret: Optional[str] = Header(default=None)):
    _check_auth(x_ops_secret)

    cid = body.cluster_id.lower()
    if cid not in ALL_CLUSTERS:
        raise HTTPException(status_code=422, detail=f"cluster_id desconhecido: {body.cluster_id!r}")

    p = body.params.model_dump()

    # I-3: fusao vive no backend — strip confianca_cruzada do node
    p.pop("confianca_cruzada", None)

    # I-1: so contagens de pessoas — strip campos ambientais se vieram
    for _f in ("co2_ppm", "temperatura", "humidade", "humidity", "temp_c"):
        p.pop(_f, None)

    # Regra unissex: wc-05/wc-06 nao tem split por genero.
    if is_unisex(cid):
        p["homens"] = None
        p["mulheres"] = None

    # Se nao veio ocupacao, mas veio pessoas_estimadas, deriva da capacidade real.
    if p.get("ocupacao_instantanea") is None and p.get("pessoas_estimadas") is not None:
        p["ocupacao_instantanea"] = occupancy_pct(cid, float(p["pessoas_estimadas"]))

    ts_ms = body.ts or int(_time.time() * 1000)
    ingest_store.put(cid, p, ts_ms)
    _run_fusion(cid, p, ts_ms)
    return {"ok": True, "cluster_id": cid, "stored_ts": ts_ms, "unisex": is_unisex(cid)}


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
