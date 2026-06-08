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

import logging
import os
import time as _time
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

from app.config import get_settings
from app.services import ingest_store
from app.clusters_capacity import ALL_CLUSTERS, is_unisex, occupancy_pct
from app.sensors_topology import USAR_IR

_logger = logging.getLogger(__name__)

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
    # Campos Opcao A — firmware envia cluster_id="wc-01" + porta + secao
    fonte: Optional[str] = "lilygo"   # "lilygo" | "luxonis" | "prosegur"
    porta: Optional[str] = None        # "LL" | "LR" | "C"  (clusters M/F)
    secao: Optional[str] = None        # "m"  | "f"  | "u"  (clusters M/F)

    class Config:
        extra = "allow"  # permite fontes cruas extra (ml, etc.) sem rejeitar


class IngestBody(BaseModel):
    cluster_id: str
    ts: Optional[int] = None
    params: IngestParams


def _check_auth(ops_secret: Optional[str], ingest_token: Optional[str]) -> None:
    # Camada 1 — X-Ops-Secret (existente, compatibilidade)
    expected_ops = get_settings().ops_secret
    if expected_ops and expected_ops != "change-me":
        if ops_secret != expected_ops:
            raise HTTPException(status_code=401, detail="invalid ops secret")
    else:
        _logger.warning("OPS_SECRET nao configurado — ingest sem autenticacao ops")

    # Camada 2 — X-Ingest-Token (nova camada; so activa se INGEST_TOKEN estiver definido)
    expected_tok = os.getenv("INGEST_TOKEN", "")
    if expected_tok:
        if ingest_token != expected_tok:
            raise HTTPException(status_code=401, detail="invalid ingest token")


def _run_fusion(cid: str, params: dict, ts_ms: int) -> None:
    """Constroi FusionInput por seccao e chama fuse_section (§3.1-3.2).

    Opcao A: quando secao esta presente, funde so essa seccao com IR acumulado.
    Luxonis (fonte=luxonis): mapeia pessoas_estimadas -> luxonis_count.
    Prosegur (fonte=prosegur): ja chega via contagem_prosegur.
    """
    try:
        from app.fusion import FusionInput, fuse_section

        usar_ir = USAR_IR.get(cid, True)
        estado  = params.get("estado_sensor", "ok")
        prosegur = params.get("contagem_prosegur")
        fonte   = (params.get("fonte") or "lilygo").lower()
        secao   = (params.get("secao") or "").lower() or None  # "m" | "f" | "u" | None

        if is_unisex(cid):
            luxonis  = params.get("pessoas_estimadas") if fonte == "luxonis" else None
            wifi_est = params.get("pessoas_estimadas") if fonte != "luxonis" else None
            fuse_section(FusionInput(
                section_id=cid,
                ts_ms=ts_ms,
                entradas_ir=None,
                saidas_ir=None,
                pessoas_estimadas=wifi_est,
                luxonis_count=luxonis,
                contagem_prosegur=prosegur,
                estado_sensor=estado,
                usar_ir=False,
            ))

        elif secao in ("m", "f"):
            # LLH/LRH/LLW/LRW: usa IR acumulado do store (soma das duas portas)
            agg   = ingest_store.get(cid)
            agg_p = agg["params"] if agg else {}
            if secao == "m":
                ir_in  = agg_p.get("entradas_ir_m")
                ir_out = agg_p.get("saidas_ir_m")
            else:
                ir_in  = agg_p.get("entradas_ir_f")
                ir_out = agg_p.get("saidas_ir_f")
            luxonis  = params.get("pessoas_estimadas") if fonte == "luxonis" else None
            wifi_est = params.get("pessoas_estimadas") if fonte == "lilygo"  else None
            fuse_section(FusionInput(
                section_id=f"{cid}_{secao}",
                ts_ms=ts_ms,
                entradas_ir=ir_in,
                saidas_ir=ir_out,
                pessoas_estimadas=wifi_est,
                luxonis_count=luxonis,
                contagem_prosegur=prosegur,
                estado_sensor=estado,
                usar_ir=usar_ir,
            ))

        else:
            # Legado: sem secao — divide WiFi por M e F, usa IR total
            homens  = params.get("homens")
            mulheres = params.get("mulheres")
            pessoas  = params.get("pessoas_estimadas")
            entradas = params.get("entradas_ir")
            saidas   = params.get("saidas_ir")
            for gender, pessoas_g in (("m", homens), ("f", mulheres)):
                wifi_est = (
                    float(pessoas_g) if pessoas_g is not None
                    else (float(pessoas) / 2.0 if pessoas is not None else None)
                )
                luxonis = (
                    float(pessoas_g) if fonte == "luxonis" and pessoas_g is not None
                    else (float(pessoas) / 2.0 if fonte == "luxonis" and pessoas is not None else None)
                )
                fuse_section(FusionInput(
                    section_id=f"{cid}_{gender}",
                    ts_ms=ts_ms,
                    entradas_ir=entradas,
                    saidas_ir=saidas,
                    pessoas_estimadas=wifi_est if fonte != "luxonis" else None,
                    luxonis_count=luxonis,
                    contagem_prosegur=prosegur,
                    estado_sensor=estado,
                    usar_ir=usar_ir,
                ))
    except Exception:
        pass   # fusao nao pode parar a ingestao


@router.post("/ingest")
async def ingest(
    body: IngestBody,
    x_ops_secret: Optional[str] = Header(default=None),
    x_ingest_token: Optional[str] = Header(default=None),
):
    _check_auth(x_ops_secret, x_ingest_token)

    cid = body.cluster_id.lower()
    if cid not in ALL_CLUSTERS:
        raise HTTPException(status_code=422, detail=f"cluster_id desconhecido: {body.cluster_id!r}")

    p = body.params.model_dump()

    # Extrair campos de roteamento Opcao A (ficam tambem em p para _run_fusion)
    porta = (p.get("porta") or "").strip().upper() or None
    secao = (p.get("secao") or "").strip().lower() or None

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
    ingest_store.put(cid, p, ts_ms, porta=porta, secao=secao)
    _run_fusion(cid, p, ts_ms)
    return {
        "ok": True, "cluster_id": cid, "stored_ts": ts_ms,
        "unisex": is_unisex(cid),
        "porta": porta, "secao": secao,
        "fonte": p.get("fonte", "lilygo"),
    }


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
