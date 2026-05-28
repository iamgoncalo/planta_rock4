"""
clusters_geo.py (router) — serve a geometria fixa dos clusters.
GET /api/v1/clusters/geo  → posições (metros + GPS), tipo, capacidades, landmarks.
Fonte de verdade: app/clusters_geo.py (único sítio para editar coordenadas).
"""
from __future__ import annotations
from fastapi import APIRouter
from app.clusters_geo import build_geo_payload

router = APIRouter(prefix="/api/v1", tags=["clusters-geo"])


@router.get("/clusters/geo")
async def clusters_geo():
    """Geometria fixa dos 8 clusters — a mesma em toda a plataforma."""
    return build_geo_payload()
