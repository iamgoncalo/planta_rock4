"""
PlantaOS — Router de INTELIGENCIA. Expoe:
  GET  /api/v1/alerts?env=rock-in-rio              — alertas em tempo real
  POST /api/v1/counterfactual                       — "e se..." cenarios
  GET  /api/v1/festival/profile?day=21-06          — perfil do dia
  GET  /api/v1/festival/days                       — todos os dias
  GET  /api/v1/festival/pressure?day=21-06&h=22    — pressao estimada
"""
from __future__ import annotations
import asyncio, time
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from app.services import alerts_engine
from app.services import counterfactuals
from app.services import festival_profile

router = APIRouter(prefix="/api/v1", tags=["intelligence"])


class CounterfactualIn(BaseModel):
    cluster: str
    cenario: str
    params: dict = {}


@router.get("/alerts")
async def alerts(env: str = Query(default="rock-in-rio")):
    """Calcula alertas em tempo real a partir do estado da frota e da fusao."""
    try:
        from app.routers.fleet import get_fleet
        from app.routers.fusion import fusion_all
        fleet_data = await get_fleet(mode=None)
        sensors = fleet_data.get("sensors", [])
        fus_data = await fusion_all(mode="sim")
        fusions = fus_data.get("clusters", {})
        return alerts_engine.calcular(sensors, fusions)
    except Exception as ex:
        return {"alertas": [], "sumario": {"crit":0,"warn":0,"info":0,"total":0},
                "erro": f"falha a calcular alertas: {ex}"}


@router.post("/counterfactual")
async def counterfactual(body: CounterfactualIn):
    """Aplica um cenario sem mexer no estado real. Devolve atual vs simulado."""
    r = counterfactuals.aplicar(body.cluster.lower(), body.cenario, **(body.params or {}))
    if "erro" in r:
        raise HTTPException(400, r["erro"])
    return r


@router.get("/counterfactual/scenarios")
async def scenarios_list():
    """Lista cenarios disponiveis com descricoes."""
    return {
        "scenarios": [
            {"id": "disable_source",
             "nome": "Desligar uma fonte",
             "descricao": "E se desligarmos a câmara ou IR ou WiFi neste cluster?",
             "params": [{"nome": "fonte", "tipo": "select", "opcoes": ["camera","ir","wifi"]}]},
            {"id": "close_cluster",
             "nome": "Fechar o cluster",
             "descricao": "Se este cluster fechar, para onde vai o fluxo?",
             "params": []},
            {"id": "surge_concert",
             "nome": "Surto pós-concerto",
             "descricao": "Simula surto de pessoas após fim do show.",
             "params": [{"nome": "multiplicador", "tipo": "number", "default": 1.6}]},
            {"id": "rain",
             "nome": "Chuva",
             "descricao": "Aumenta permanência +40%.",
             "params": []},
            {"id": "gateway_down",
             "nome": "Gateway caiu",
             "descricao": "LilyGo perdeu energia — todos os IR perdidos.",
             "params": []},
        ]
    }


@router.get("/festival/days")
async def festival_days():
    return {"days": festival_profile.todos()}


@router.get("/festival/profile")
async def festival_profile_get(day: str = Query(default=None)):
    return festival_profile.perfil(day)


@router.get("/festival/pressure")
async def festival_pressure(day: str = Query(...), h: float = Query(...)):
    return festival_profile.pressao_estimada(day, h)
