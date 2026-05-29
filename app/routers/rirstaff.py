"""
PlantaOS — RIR STAFF: ingestao real das casas de banho do staff.
Recebe telemetria do LilyGo (contadores acumulados, idempotente). Calcula
ocupacao por capacidade, ao segundo. Guarda em memoria (live 24h). Distingue
sempre dados REAIS (vieram do hardware) do estado vazio.

Endpoints:
  POST /api/v1/ingest_staff/{cluster} LilyGo envia estado (entradas/saidas/rssi)
  GET  /api/v1/rirstaff             estado das 2 casas de banho do staff
  GET  /api/v1/rirstaff/{cluster}   estado de uma
  POST /api/v1/rirstaff/{cluster}/capacidade?valor=8   calibrar capacidade
  POST /api/v1/rirstaff/{cluster}/reset                zerar contadores
"""
from __future__ import annotations
import time, threading
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["rirstaff"])
_LOCK = threading.Lock()

# Config das 2 casas de banho do staff (configuravel)
STAFF = {
    "rirstaff-m": {"nome": "Staff · Homens", "genero": "M", "capacidade": 8},
    "rirstaff-f": {"nome": "Staff · Mulheres", "genero": "F", "capacidade": 8},
}

# Estado vivo recebido do hardware: cluster -> {dados, ts_server}
_LIVE: dict[str, dict] = {}
# Offset para reset: cluster -> {entradas, saidas} a subtrair
_RESET_OFFSET: dict[str, dict] = {}


class Porta(BaseModel):
    entradas: int = 0
    saidas: int = 0


class IngestIn(BaseModel):
    cluster: str | None = None
    portas: dict = {}            # {"porta-1": {"entradas":N,"saidas":M}}
    ocupacao: int | None = None  # opcional: LilyGo ja calculou
    capacidade: int | None = None
    rssi: float | None = None
    uptime_s: float | None = None
    fw: str | None = None


def _estado(ocup: int, cap: int) -> str:
    if cap <= 0: return "—"
    pct = ocup / cap * 100
    if pct >= 100: return "cheio"
    if pct >= 75: return "quase cheio"
    if pct >= 40: return "moderado"
    return "livre"


def _calc(cluster: str, dados: dict) -> dict:
    cfg = STAFF.get(cluster, {"nome": cluster, "genero": "?", "capacidade": 8})
    cap = cfg["capacidade"]
    # somar entradas/saidas de todas as portas
    tot_in = tot_out = 0
    for p, v in (dados.get("portas") or {}).items():
        tot_in += int(v.get("entradas", 0))
        tot_out += int(v.get("saidas", 0))
    # aplicar offset de reset
    off = _RESET_OFFSET.get(cluster, {"entradas": 0, "saidas": 0})
    tot_in -= off["entradas"]; tot_out -= off["saidas"]
    # ocupacao: usar a do LilyGo se enviada, senao calcular
    if dados.get("ocupacao") is not None:
        ocup = max(0, int(dados["ocupacao"]))
    else:
        ocup = max(0, tot_in - tot_out)
    return {
        "cluster": cluster, "nome": cfg["nome"], "genero": cfg["genero"],
        "entradas": tot_in, "saidas": tot_out,
        "ocupacao": ocup, "capacidade": cap,
        "ocupacao_pct": round(ocup / cap * 100, 1) if cap else 0,
        "estado": _estado(ocup, cap),
        "rssi_dbm": dados.get("rssi"),
        "uptime_s": dados.get("uptime_s"),
        "fw": dados.get("fw"),
    }


@router.post("/ingest_staff/{cluster}")
async def ingest(cluster: str, body: IngestIn):
    """O LilyGo chama isto a cada 1-2s com o estado acumulado."""
    cluster = cluster.lower()
    t = time.time()
    dados = body.model_dump()
    with _LOCK:
        _LIVE[cluster] = {"dados": dados, "ts_server": t}
        # capacidade auto-config se o device a enviar e e cluster conhecido
        if body.capacidade and cluster in STAFF:
            STAFF[cluster]["capacidade"] = int(body.capacidade)
    calc = _calc(cluster, dados)
    return {"ok": True, "ocupacao": calc["ocupacao"], "estado": calc["estado"],
            "capacidade": calc["capacidade"], "ts": t}


def _snapshot(cluster: str) -> dict:
    rec = _LIVE.get(cluster)
    cfg = STAFF.get(cluster, {"nome": cluster, "genero": "?", "capacidade": 8})
    if not rec:
        return {"cluster": cluster, "nome": cfg["nome"], "genero": cfg["genero"],
                "capacidade": cfg["capacidade"], "data_origin": "sem-dados",
                "online": False, "ocupacao": None,
                "mensagem": "À espera do LilyGo — nenhum dado recebido ainda"}
    age = time.time() - rec["ts_server"]
    calc = _calc(cluster, rec["dados"])
    calc["data_origin"] = "real"
    calc["online"] = age < 15
    calc["age_s"] = round(age, 1)
    if age >= 15:
        calc["mensagem"] = f"Sem transmitir há {int(age)}s — verificar LilyGo/WiFi"
    return calc


@router.get("/rirstaff")
async def rirstaff_all():
    return {"casas_de_banho": [_snapshot(c) for c in STAFF], "ts": time.time()}


@router.get("/rirstaff/{cluster}")
async def rirstaff_one(cluster: str):
    cluster = cluster.lower()
    if cluster not in STAFF:
        raise HTTPException(404, f"casa de banho desconhecida: {cluster}")
    return _snapshot(cluster)


@router.post("/rirstaff/{cluster}/capacidade")
async def set_capacidade(cluster: str, valor: int = Query(..., ge=1, le=100)):
    cluster = cluster.lower()
    if cluster not in STAFF:
        raise HTTPException(404, f"desconhecida: {cluster}")
    with _LOCK:
        STAFF[cluster]["capacidade"] = valor
    return {"cluster": cluster, "capacidade": valor}


@router.post("/rirstaff/{cluster}/reset")
async def reset_counters(cluster: str):
    """Zera os contadores (offset) — usa quando recalibras no local."""
    cluster = cluster.lower()
    rec = _LIVE.get(cluster)
    if rec:
        dados = rec["dados"]
        tot_in = sum(int(v.get("entradas",0)) for v in (dados.get("portas") or {}).values())
        tot_out = sum(int(v.get("saidas",0)) for v in (dados.get("portas") or {}).values())
        with _LOCK:
            _RESET_OFFSET[cluster] = {"entradas": tot_in, "saidas": tot_out}
    return {"cluster": cluster, "reset": True}
