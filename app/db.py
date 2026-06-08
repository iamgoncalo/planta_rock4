from __future__ import annotations
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine():
    url = get_settings().database_url
    if not url:
        return None
    return create_async_engine(url, echo=False, pool_pre_ping=True)


engine = _engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False) if engine is not None else None


async def get_db() -> AsyncSession:
    if AsyncSessionLocal is None:
        raise RuntimeError("DATABASE_URL não configurado")
    async with AsyncSessionLocal() as session:
        yield session
