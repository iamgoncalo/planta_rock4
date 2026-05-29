"""
PlantaOS — RIR STAFF: ingestao real das casas de banho do staff.
v2: aceita o ESQUEMA CANONICO de KPIs (cluster_id + params) e tambem o
formato antigo {portas}. Faz fusao honesta de fontes (IR / camara / wifi /
prosegur) e calcula confianca cruzada. Live 24h, em memoria.

ESQUEMA CANONICO (recomendado, o que o LilyGo envia):
{
  "cluster_id": "rirstaff-m",
  "ts": 1634712287000,
  "params": {
    "telemoveis_detectados": 34, "pessoas_estimadas": 25,
    "homens": 12, "mulheres": 13,
    "entradas_ir": 22, "saidas_ir": 14,
    "ocupacao_instantanea": 8, "contagem_prosegur": 0,
    "confianca_cruzada": 0.8, "estado_sensor": "okay",
    "rssi": -58, "uptime_s": 3600, "fw": "rirstaff-1.0"
  }
}
"""
from __future__ import annotations
import time, threading
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["rirstaff"])
_LOCK = threading.Lock()

STAFF = {
    "rirstaff-m": {"nome": "Staff · Homens", "genero": "M", "capacidade": 8},
    "rirstaff-f": {"nome": "Staff · Mulheres", "genero": "F", "capacidade": 8},
}

_LIVE: dict[str, dict] = {}
_RESET_OFFSET: dict[str, dict] = {}


class IngestIn(BaseModel):
    # esquema canonico
    cluster_id: str | None = None
    ts: float | None = None
    params: dict | None = None
    # formato antigo (retrocompat)
    cluster: str | None = None
    portas: dict | None = None
    ocupacao: int | None = None
    capacidade: int | None = None
    rssi: float | None = None
    uptime_s: float | None = None
    fw: str | None = None


def _estado(ocup, cap) -> str:
    if cap <= 0 or ocup is None: return "—"
    pct = ocup / cap * 100
    if pct >= 100: return "cheio"
    if pct >= 75: return "quase cheio"
    if pct >= 40: return "moderado"
    return "livre"


def _normaliza(body: IngestIn) -> dict:
    """Junta os dois formatos num dict de params canonico."""
    p = dict(body.params or {})
    # formato antigo {portas} -> somar para entradas_ir / saidas_ir
    if body.portas:
        tin = sum(int(v.get("entradas", 0)) for v in body.portas.values())
        tout = sum(int(v.get("saidas", 0)) for v in body.portas.values())
        p.setdefault("entradas_ir", tin)
        p.setdefault("saidas_ir", tout)
    if body.ocupacao is not None:
        p.setdefault("ocupacao_instantanea", body.ocupacao)
    # metadados de ligacao
    if body.rssi is not None: p.setdefault("rssi", body.rssi)
    if body.uptime_s is not None: p.setdefault("uptime_s", body.uptime_s)
    if body.fw: p.setdefault("fw", body.fw)
    return p


def _fusao(cluster: str, p: dict) -> dict:
    """Fusao honesta -> ocupacao + confianca cruzada."""
    cfg = STAFF.get(cluster, {"nome": cluster, "genero": "?", "capacidade": 8})
    cap = cfg["capacidade"]

    ir_in = p.get("entradas_ir")
    ir_out = p.get("saidas_ir")
    # aplicar offset de reset
    off = _RESET_OFFSET.get(cluster, {"entradas": 0, "saidas": 0})
    ocup_ir = None
    if ir_in is not None and ir_out is not None:
        ocup_ir = max(0, int(ir_in) - off["entradas"] - (int(ir_out) - off["saidas"]))

    ocup_inst = p.get("ocupacao_instantanea")
    pess_est = p.get("pessoas_estimadas")

    # prioridade: ocupacao_instantanea explicita > IR > pessoas_estimadas
    fontes = []
    if ocup_inst is not None: fontes.append(("instantanea", int(ocup_inst)))
    if ocup_ir is not None: fontes.append(("ir", ocup_ir))
    if pess_est is not None: fontes.append(("estimada", int(pess_est)))

    if not fontes:
        ocup = None
    else:
        ocup = fontes[0][1]

    # confianca cruzada: se enviada, usa; senao calcula da concordancia entre fontes
    conf = p.get("confianca_cruzada")
    if conf is None and len(fontes) >= 2:
        vals = [v for _, v in fontes]
        spread = max(vals) - min(vals)
        base = max(1, max(vals))
        conf = round(max(0.0, 1.0 - spread / base), 2)
    elif conf is None:
        conf = 1.0 if fontes else 0.0

    return {
        "cluster": cluster, "nome": cfg["nome"], "genero": cfg["genero"],
        "capacidade": cap,
        "ocupacao": ocup,
        "ocupacao_pct": round(ocup / cap * 100, 1) if (ocup is not None and cap) else None,
        "estado": _estado(ocup, cap),
        "fontes": {nome: val for nome, val in fontes},
        "entradas_ir": ir_in, "saidas_ir": ir_out, "ocupacao_ir": ocup_ir,
        "telemoveis_detectados": p.get("telemoveis_detectados"),
        "pessoas_estimadas": pess_est,
        "homens": p.get("homens"), "mulheres": p.get("mulheres"),
        "contagem_prosegur": p.get("contagem_prosegur"),
        "confianca_cruzada": conf,
        "estado_sensor": p.get("estado_sensor", "okay"),
        "rssi_dbm": p.get("rssi"),
        "uptime_s": p.get("uptime_s"),
        "fw": p.get("fw"),
    }


@router.post("/ingest_staff/{cluster}")
async def ingest(cluster: str, body: IngestIn):
    cluster = (cluster or body.cluster_id or body.cluster or "").lower()
    if not cluster:
        raise HTTPException(400, "cluster_id em falta")
    t = time.time()
    p = _normaliza(body)
    with _LOCK:
        _LIVE[cluster] = {"params": p, "ts_server": t}
        if body.capacidade and cluster in STAFF:
            STAFF[cluster]["capacidade"] = int(body.capacidade)
    f = _fusao(cluster, p)
    return {"ok": True, "ocupacao": f["ocupacao"], "estado": f["estado"],
            "capacidade": f["capacidade"], "confianca_cruzada": f["confianca_cruzada"], "ts": t}


def _snapshot(cluster: str) -> dict:
    rec = _LIVE.get(cluster)
    cfg = STAFF.get(cluster, {"nome": cluster, "genero": "?", "capacidade": 8})
    if not rec:
        return {"cluster": cluster, "nome": cfg["nome"], "genero": cfg["genero"],
                "capacidade": cfg["capacidade"], "data_origin": "sem-dados",
                "online": False, "ocupacao": None,
                "mensagem": "À espera do LilyGo — nenhum dado recebido ainda"}
    age = time.time() - rec["ts_server"]
    f = _fusao(cluster, rec["params"])
    f["data_origin"] = "real"
    f["online"] = age < 30
    f["age_s"] = round(age, 1)
    if age >= 30:
        f["mensagem"] = f"Sem transmitir há {int(age)}s — verificar LilyGo/WiFi"
    return f


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
    cluster = cluster.lower()
    rec = _LIVE.get(cluster)
    if rec:
        p = rec["params"]
        with _LOCK:
            _RESET_OFFSET[cluster] = {"entradas": int(p.get("entradas_ir", 0)),
                                      "saidas": int(p.get("saidas_ir", 0))}
    return {"cluster": cluster, "reset": True}

# ============================================================================
# CALIBRACAO REMOTA — adicionado para PlantaOS Staff (calibrar sem cabo)
# O sensor le GET /rirstaff/config/{cluster}; tu mudas com POST (password).
# ============================================================================
import os as _os, json as _json, time as _time
from pydantic import BaseModel as _BaseModel
from fastapi import HTTPException as _HTTPException

_ADMIN_PASS = _os.getenv("RIRSTAFF_ADMIN_PASS", "planta2026")
_CFG_FILE = _os.getenv("RIRSTAFF_CONFIG_FILE", "/tmp/rirstaff_config.json")
_CFG_DEFAULT = {
    "rirstaff-f": {"raio_m": 5, "divisor": 3, "baseline": 0, "capacidade": 8, "contexto": "staff"},
    "rirstaff-m": {"raio_m": 5, "divisor": 3, "baseline": 0, "capacidade": 8, "contexto": "staff"},
}
def _cfg_load():
    try:
        with open(_CFG_FILE) as f: return _json.load(f)
    except Exception: return dict(_CFG_DEFAULT)
def _cfg_save(c):
    try:
        with open(_CFG_FILE, "w") as f: _json.dump(c, f)
    except Exception: pass

@router.get("/rirstaff/config/{cluster}")
def rirstaff_get_config(cluster: str):
    c = _cfg_load()
    return c.get(cluster, _CFG_DEFAULT.get(cluster, _CFG_DEFAULT["rirstaff-f"]))

class _CfgUpd(_BaseModel):
    password: str
    raio_m: int | None = None
    divisor: int | None = None
    baseline: int | None = None
    capacidade: int | None = None
    contexto: str | None = None

@router.post("/rirstaff/config/{cluster}")
def rirstaff_set_config(cluster: str, upd: _CfgUpd):
    if upd.password != _ADMIN_PASS:
        raise _HTTPException(status_code=401, detail="Password errada")
    c = _cfg_load()
    a = c.get(cluster, dict(_CFG_DEFAULT.get(cluster, _CFG_DEFAULT["rirstaff-f"])))
    if upd.raio_m is not None: a["raio_m"] = max(1, min(30, upd.raio_m))
    if upd.divisor is not None: a["divisor"] = max(1, min(6, upd.divisor))
    if upd.baseline is not None: a["baseline"] = max(0, upd.baseline)
    if upd.capacidade is not None: a["capacidade"] = max(1, upd.capacidade)
    if upd.contexto is not None: a["contexto"] = upd.contexto
    a["atualizado"] = int(_time.time())
    c[cluster] = a
    _cfg_save(c)
    return {"ok": True, "cluster": cluster, "config": a}
