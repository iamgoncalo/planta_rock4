"""
PlantaOS — modelos de histórico de fluxo e perfis de multidão.
Duas tabelas: flow_snapshots (série temporal 60s) + crowd_profiles (seed estático).
"""
from __future__ import annotations

from sqlalchemy import Column, Integer, SmallInteger, String, Float, Date, Index, func, text
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.db import Base


class FlowSnapshot(Base):
    """Snapshot de fluxo por secção, gravado a cada 60s nos dias de festival."""
    __tablename__ = "flow_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    festival_day = Column(Date, nullable=False)
    hour = Column(SmallInteger, nullable=False)
    cluster_id = Column(String(10), nullable=False)
    secao = Column(String(4), nullable=False)
    ocupacao_pct = Column(Float, nullable=True)
    fluxo_entrada = Column(Float, nullable=True)
    fluxo_saida = Column(Float, nullable=True)
    fila = Column(Integer, nullable=True)
    confianca_pct = Column(Float, nullable=True)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_flow_snap_day_hour_cluster", "festival_day", "hour", "cluster_id"),
    )


class CrowdProfile(Base):
    """Perfil de multidão esperado por dia + hora do festival (seed estático)."""
    __tablename__ = "crowd_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    festival_day = Column(Date, nullable=False)
    hour = Column(SmallInteger, nullable=False)
    show_name = Column(String(100), nullable=True)
    palco = Column(String(50), nullable=True)
    expected_attendance = Column(Integer, nullable=True)
    surge_factor = Column(Float, nullable=True, server_default=text("1.0"))

    __table_args__ = (
        Index("ix_crowd_day_hour", "festival_day", "hour"),
    )
