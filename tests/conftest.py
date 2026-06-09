"""Shared pytest fixtures for PlantaOS test suite."""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app


def pytest_configure(config):
    """Suite hermética: garante tabelas + seed na BD de teste (uma vez).

    O ASGITransport não corre os eventos de startup da app, por isso o
    create_all + seed (que em produção acontecem no arranque) são feitos aqui.
    """
    async def _bootstrap():
        from app.db import engine, Base, AsyncSessionLocal
        if engine is None:
            return
        from app.models.db import operations, sensors, flow_history  # noqa: F401
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        from app.startup_seeds import seed_sensors_if_empty
        await seed_sensors_if_empty(AsyncSessionLocal)

    try:
        asyncio.run(_bootstrap())
    except Exception:
        pass  # sem DATABASE_URL, os testes que precisam de BD falham com clareza


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """AsyncClient backed by the ASGI app — no real HTTP server needed."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
