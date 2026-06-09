"""
PlantaOS · DB models para operações
====================================
Tabelas: cleaning_log, staff_roster, incident_log, ingest_snapshots
Segue o padrão de app/models/db/sensors.py — SQLAlchemy clássico.
"""
from __future__ import annotations

from sqlalchemy import (
    Column, String, Integer, Boolean, Text, ForeignKey, BigInteger, Float, func, text,
    JSON, Index,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, JSONB as _PGJSONB

# JSONB em Postgres, JSON em SQLite (dev/teste) — DDL idêntica em produção
JSONB = _PGJSONB().with_variant(JSON(), "sqlite")

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


# ============================================================================
# INGEST SNAPSHOT — snapshot do ingest_store para sobreviver restarts (U5)
# ============================================================================
class IngestSnapshot(Base):
    """Última leitura conhecida por cluster — persistida a cada 60s."""
    __tablename__ = "ingest_snapshots"

    cluster_id = Column(String, primary_key=True)
    params_json = Column(JSONB, nullable=False)
    ts_server   = Column(BigInteger, nullable=False)   # unix ms
    ts_device   = Column(BigInteger, nullable=True)    # unix ms
    updated_at  = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                         onupdate=func.now())


# ============================================================================
# FUSÃO ROLANTE — snapshot por secção para sobreviver restarts
# ============================================================================
class FusaoRolanteSnapshot(Base):
    """Estado da fusão rolante (regressão + âncora + nós) por secção — 60s."""
    __tablename__ = "fusao_rolante_snapshots"

    section_id = Column(String, primary_key=True)      # ex. "wc-01_m", "wc-05"
    state_json = Column(JSON, nullable=False)          # JSON genérico (PG+SQLite)
    ts_server  = Column(BigInteger, nullable=False)    # unix ms
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                        onupdate=func.now())


# ============================================================================
# SECTION HISTORY — 1 registo/min por secção · retenção 7 dias (onda 5a)
# Migrações ADITIVAS: nenhum deploy apaga este histórico.
# ============================================================================
class SectionHistory(Base):
    """Memória operacional ao minuto: o sistema lembra-se de TUDO."""
    __tablename__ = "section_history"
    __table_args__ = (Index("ix_secthist_sec_ts", "section_id", "ts_ms"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    section_id = Column(String, nullable=False)        # "wc-01_m" | "wc-05"
    ts_ms = Column(BigInteger, nullable=False)         # minuto, unix ms UTC
    ocupacao = Column(Float, nullable=False, server_default=text("0"))
    fila = Column(Float, nullable=False, server_default=text("0"))
    espera_prevista_min = Column(Float, nullable=False, server_default=text("0"))
    confianca = Column(Float, nullable=False, server_default=text("0"))
    a_actual = Column(Float, nullable=False, server_default=text("0"))
    alertas = Column(JSON, nullable=True)              # ["WARN_FILA", ...]


# ============================================================================
# DECISION LOG — auditoria total (onda 5b): nada acontece sem rasto
# ============================================================================
class DecisionLog(Base):
    """Toda a decisão do motor e todo o comando do operador, com antes/depois."""
    __tablename__ = "decision_log"
    __table_args__ = (Index("ix_declog_ts", "ts_ms"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_ms = Column(BigInteger, nullable=False)         # unix ms UTC
    tipo = Column(String, nullable=False)
    # tipo: alerta_warn | alerta_crit | troca_recomendacao | pre_surto |
    #       modo_degradado | cluster_fechado | cluster_reaberto | desvio
    origem = Column(String, nullable=False, server_default=text("'motor'"))
    # origem: motor | operador
    utilizador = Column(String, nullable=True)         # obrigatório p/ operador
    seccao = Column(String, nullable=True)
    antes = Column(JSON, nullable=True)
    depois = Column(JSON, nullable=True)
    justificacao = Column(Text, nullable=True)


# ============================================================================
# NODE CALIBRATION — factor k por nó WiFi (fusão rolante)
# ============================================================================
class NodeCalibration(Base):
    """Calibração de um nó WiFi: k (default 1.0), rssi_1m, threshold_dbm."""
    __tablename__ = "node_calibration"

    node_id = Column(String, primary_key=True)         # ex. "wc-01_m_porta"
    cluster_id = Column(String, nullable=False)
    secao = Column(String, nullable=False)             # "m" | "f" | "u"
    k = Column(Float, nullable=False, server_default=text("1.0"))
    rssi_1m = Column(Float, nullable=True)
    threshold_dbm = Column(Float, nullable=True)
    actualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(),
                            onupdate=func.now())
