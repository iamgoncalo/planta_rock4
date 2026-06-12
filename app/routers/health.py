"""
PlantaOS · Health endpoint
=================================
Devolve estado público do serviço sem expor a palavra "simulation".
"""
from __future__ import annotations

import os
import time

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["health"])

# Data de instalação dos sensores físicos (Rock in Rio Lisboa 2026)
HARDWARE_INSTALL_DATE = "2026-06-11"


@router.get("/health")
async def health() -> dict:
    """Estado do backend. data_source indica origem dos números:
    - 'awaiting_hardware' antes de 11 Junho (sensores físicos a instalar)
    - 'live' depois de instalados
    """
    s = get_settings()
    # Compatibilidade: setting interno chama-se simulation_active mas externamente
    # expomos data_source semántico
    is_pre_install = bool(getattr(s, "simulation_active", True))
    return {
        "status": "ok",
        "version": getattr(s, "version", "0.1.0"),
        # sha curto do commit em produção (Railway injecta a env var) —
        # nunca mais adivinhamos que código está deployado
        "git_sha": (os.getenv("RAILWAY_GIT_COMMIT_SHA") or "dev")[:7],
        "data_source": "awaiting_hardware" if is_pre_install else "live",
        "hardware_install_date": HARDWARE_INSTALL_DATE,
        "ts": time.time(),
    }
