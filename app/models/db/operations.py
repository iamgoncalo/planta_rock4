"""
PlantaOS · DB models para operações
====================================
3 tabelas novas: cleaning_log, staff_roster, incident_log
Segue o padrão de app/models/db/sensors.py — SQLAlchemy clássico.
"""
from __future__ import annotations

from sqlalchemy import (
    Column, String, Integer, Boolean, Text, ForeignKey, func, text
)
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.db import Base


# ============================================================================
# CLEANING — Estado de limpeza por cluster
# ============================================================================
class CleaningLog(Base):
    """Cada linha = um evento de limpeza (concluído ou agendado)."""
    __tablename__ = "cleaning_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(String, ForeignKey("cluster_refs.id", ondelete="SET NULL"), nullable=False)
    cleaned_at = Column(TIMESTAMP(timezone=True), nullable=True)
    scheduled_for = Column(TIMESTAMP(timezone=True), nullable=True)
    status = Column(String, nullable=False, server_default=text("'clean'"))
    # status: clean | in_progress | needs_cleaning | urgent
    team = Column(String, nullable=True)
    operator = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


# ============================================================================
# STAFF — Roster de pessoas por cluster e turno
# ============================================================================
class StaffRoster(Base):
    """Alocação de staff a um cluster, num determinado turno."""
    __tablename__ = "staff_roster"

    id = Column(Integer, primary_key=True, autoincrement=True)
    day = Column(String, nullable=False)  # "2026-06-20"
    cluster_id = Column(String, ForeignKey("cluster_refs.id", ondelete="SET NULL"), nullable=False)
    shift_start = Column(String, nullable=False)  # "14:00"
    shift_end = Column(String, nullable=False)    # "18:00"
    role = Column(String, nullable=False)         # cleaning | steward | medic | security
    name = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    confirmed = Column(Boolean, server_default=text("false"))
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


# ============================================================================
# INCIDENTS — Registo de incidentes
# ============================================================================
class IncidentLog(Base):
    """Cada linha = um incidente reportado no terreno."""
    __tablename__ = "incident_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(String, ForeignKey("cluster_refs.id", ondelete="SET NULL"), nullable=True)
    severity = Column(String, nullable=False, server_default=text("'info'"))
    # severity: info | warning | critical
    category = Column(String, nullable=False)
    # category: medical | crowd | safety | hygiene | technical | other
    note = Column(Text, nullable=False)
    reported_by = Column(String, nullable=True)
    resolved = Column(Boolean, server_default=text("false"))
    resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    resolved_by = Column(String, nullable=True)
    resolution_note = Column(Text, nullable=True)
    occurred_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
