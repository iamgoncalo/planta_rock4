"""
PlantaOS — Router de AMBIENTES (espacos de trabalho de sensores).
U3 audit: lê de ingest_store + env_store por ambiente. Justificadamente separado. ✅
  GET    /api/v1/envs                      lista
  POST   /api/v1/envs                      criar {nome, modo, refresh_ms}
  GET    /api/v1/envs/{id}                 detalhe + sensores
  DELETE /api/v1/envs/{id}                 apagar (rock-in-rio nao)
  POST   /api/v1/envs/{id}/sensors         add {id,tipo,label,cluster?}
  DELETE /api/v1/envs/{id}/sensors/{sid}   remover
  GET    /api/v1/envs/{id}/fleet           frota DESTE ambiente (sim/real)
  GET    /api/v1/lobby                      sinais orfaos (via B)

rock-in-rio: frota = os 78 do registry (sim) — reaproveita o fleet existente.
ambientes custom: frota = os sensores que adicionaste; estado sim (coerente) ou
real (do ingest/lobby). Latencia: cada ambiente tem o seu refresh_ms.
"""
from __future__ import annotations
import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services import env_store as es
from app.services import fleet_sim as sim
from app.services import capabilities as caps

router = APIRouter(prefix="/api/v1", tags=["environments"])


class EnvIn(BaseModel):
    nome: str
    modo: str = "real"
    refresh_ms: int = 1500


class SensorIn(BaseModel):
    id: str
    tipo: str = "lilygo"
    label: str = ""
    cluster: str = ""


@router.get("/envs")
async def list_envs():
    return {"envs": es.list_envs()}


@router.post("/envs")
async def create_env(body: EnvIn):
    return es.create_env(body.nome, body.modo, body.refresh_ms)


@router.get("/envs/{env_id}")
async def get_env(env_id: str):
    e = es.get_env(env_id)
    if not e:
        raise HTTPException(404, f"ambiente desconhecido: {env_id}")
    return e


@router.delete("/envs/{env_id}")
async def delete_env(env_id: str):
    ok = es.delete_env(env_id)
    if not ok:
        raise HTTPException(400, "nao e possivel apagar este ambiente")
    return {"deleted": env_id}


@router.post("/envs/{env_id}/sensors")
async def add_sensor(env_id: str, body: SensorIn):
    s = es.add_sensor(env_id, body.id, body.tipo, body.label, body.cluster)
    if not s:
        raise HTTPException(400, "nao adicionado (ambiente fixo, inexistente, ou sensor repetido)")
    return s


@router.delete("/envs/{env_id}/sensors/{sid}")
async def remove_sensor(env_id: str, sid: str):
    return {"removed": es.remove_sensor(env_id, sid)}


@router.get("/envs/{env_id}/fleet")
async def env_fleet(env_id: str):
    e = es.get_env(env_id)
    if not e:
        raise HTTPException(404, f"ambiente desconhecido: {env_id}")
    modo = e["modo"]
    t = time.time()

    # rock-in-rio: reusa o fleet completo (78)
    if env_id == "rock-in-rio":
        try:
            from app.routers.fleet import get_fleet
            data = await get_fleet(mode=modo)
            data["env"] = env_id
            data["refresh_ms"] = e["refresh_ms"]
            return data
        except Exception as ex:
            raise HTTPException(500, f"erro a obter frota do festival: {ex}")

    # ambiente custom: so os sensores adicionados — distincao HONESTA real/simulado
    sensors = es.env_sensors(env_id)
    try:
        from app.services import ingest_store
    except Exception:
        ingest_store = None
    out = []
    n_real = n_sim = n_mudo = 0
    for s in sensors:
        item = dict(s)
        age = None
        if ingest_store:
            rec = ingest_store.get(s["id"])
            if rec:
                age = time.time() - rec.get("ts_server", 0)
        # 1) dado real recente?
        if age is not None and age <= 60:
            item["data_origin"] = "real"
            item["status"] = "online" if age <= 15 else "degraded"
            item["age_s"] = round(age, 1)
            item["origem"] = "real"
            n_real += 1
        elif modo == "real":
            item["data_origin"] = "real-mudo"
            item["status"] = "sem-dados"
            item["origem"] = "real"
            if age is not None:
                item["age_s"] = round(age, 1)
            n_mudo += 1
        else:
            st = sim.sim_sensor_state(s["id"], s["tipo"], t)
            item["data_origin"] = "simulado"
            item["status"] = st["status"]
            item["uptime_s"] = st["uptime_s"]
            item["rssi_dbm"] = st["rssi_dbm"]
            if st["battery"] is not None:
                item["battery"] = {"pct": st["battery"], "fonte": "simulado"}
            item["origem"] = "simulado"
            n_sim += 1
        out.append(item)
    return {"env": env_id, "modo": modo, "refresh_ms": e["refresh_ms"],
            "total": len(out), "ts": t, "sensors": out,
            "reais": n_real, "simulados": n_sim, "reais_mudos": n_mudo}



class BulkGenIn(BaseModel):
    prefixo: str
    tipo: str = "ir"
    quantidade: int = 8
    inicio: int = 1


class BulkListIn(BaseModel):
    sensores: list  # [{id,tipo,label?,cluster?}]


@router.post("/envs/{env_id}/sensors/bulk_gen")
async def add_bulk_gen(env_id: str, body: BulkGenIn):
    """Gera N sensores sequenciais (ex: prefixo wc-02, tipo ir, qtd 8 -> wc-02-ir-1..8)."""
    if not es.get_env(env_id):
        raise HTTPException(404, f"ambiente desconhecido: {env_id}")
    ids = es.gerar_ids(body.prefixo, body.tipo, max(1, min(50, body.quantidade)), body.inicio)
    return es.add_sensors_bulk(env_id, ids)


@router.post("/envs/{env_id}/sensors/bulk_list")
async def add_bulk_list(env_id: str, body: BulkListIn):
    """Adiciona uma lista de sensores de uma vez (colar lista)."""
    if not es.get_env(env_id):
        raise HTTPException(404, f"ambiente desconhecido: {env_id}")
    return es.add_sensors_bulk(env_id, body.sensores)


@router.get("/sensorcaps/{sensor_id}")
async def sensor_capabilities(sensor_id: str, tipo: str = "lilygo", cluster: str = "", rssi: float = None):
    """Capacidades de um sensor: alcance, ligacao, cobertura, saude (datasheet)."""
    return caps.capability(sensor_id, tipo, cluster or None, rssi)


@router.get("/network/coverage")
async def network_coverage():
    """Resumo da rede: alcances, topologia, cobertura por cluster (datasheet)."""
    return caps.resumo_rede()


@router.get("/network/cluster/{cluster_id}")
async def cluster_coverage(cluster_id: str):
    """Cobertura e ligacao de um cluster."""
    r = caps.cobertura_cluster(cluster_id.lower())
    if "erro" in r:
        raise HTTPException(404, r["erro"])
    return r


@router.get("/lobby")
async def lobby():
    return {"lobby": es.get_lobby()}
