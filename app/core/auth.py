"""
PlantaOS · Auth simples por API key
====================================
Protege endpoints de escrita (POST/PATCH/DELETE) com header X-Planta-Ops-Key.
A key vem da env var PLANTA_OPS_KEY (mete no Railway).

GETs públicos continuam públicos. Só endpoints que modificam dados ou disparam
acções (cleaning done, incidents, staff roster) requerem a key.

Para evitar lock-out em dev: se PLANTA_OPS_KEY não estiver definida no env,
o sistema permite todas as chamadas (modo aberto). Em produção, define a env
var e tudo fica protegido.
"""
from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException, status


def _expected_key() -> str | None:
    """Devolve a key esperada ou None se não estiver configurada."""
    val = os.getenv("PLANTA_OPS_KEY", "").strip()
    return val if val else None


async def require_ops_key(
    x_planta_ops_key: str | None = Header(default=None, alias="X-Planta-Ops-Key"),
) -> str:
    """FastAPI dependency: lê header X-Planta-Ops-Key e valida.

    Modo dev (PLANTA_OPS_KEY não set): aceita qualquer chamada, devolve "open".
    Modo prod (PLANTA_OPS_KEY set): exige header X-Planta-Ops-Key igual à env.
    """
    expected = _expected_key()
    if expected is None:
        # Modo aberto — desenvolvimento ou primeiro setup
        return "open"

    if not x_planta_ops_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header X-Planta-Ops-Key em falta",
        )

    if not secrets.compare_digest(x_planta_ops_key, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key inválida",
        )

    return "ok"
