"""
PlantaOS — Router de AMBIENTES (espacos de trabalho de sensores).
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

    # ambiente custom: so os sensores adicionados
    sensors = es.env_sensors(env_id)
    out = []
    for s in sensors:
        item = dict(s)
        if modo == "sim":
            st = sim.sim_sensor_state(s["id"], s["tipo"], t)
            item["status"] = st["status"]
            item["uptime_s"] = st["uptime_s"]
            item["rssi_dbm"] = st["rssi_dbm"]
            if st["battery"] is not None:
                item["battery"] = {"pct": st["battery"], "fonte": "simulado"}
            item["origem"] = "simulado"
        else:
            # real: estado do ingest_store por id do sensor
            item["origem"] = "real"
            try:
                from app.services import ingest_store
                rec = ingest_store.get(s["id"])
                if rec:
                    age = time.time() - rec.get("ts_server", 0)
                    item["status"] = "online" if age < 15 else "degraded" if age < 60 else "offline"
                    item["age_s"] = round(age, 1)
                else:
                    item["status"] = "sem-dados"
            except Exception:
                item["status"] = "sem-dados"
        out.append(item)
    return {"env": env_id, "modo": modo, "refresh_ms": e["refresh_ms"],
            "total": len(out), "ts": t, "sensors": out}


@router.get("/lobby")
async def lobby():
    return {"lobby": es.get_lobby()}
