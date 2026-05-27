from __future__ import annotations
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, Text, BigInteger,
    ForeignKey, func, text
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.db import Base


class ClusterRef(Base):
    __tablename__ = "cluster_refs"

    id = Column(String, primary_key=True)
    name = Column(String)


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(String, primary_key=True)
    cluster_id = Column(String, ForeignKey("cluster_refs.id", ondelete="SET NULL"), nullable=True)
    type = Column(String, nullable=False)
    model = Column(String, nullable=False)
    protocol = Column(String)
    location_desc = Column(String)
    gps_lat = Column(Float)
    gps_lon = Column(Float)
    height_cm = Column(Integer)
    gpio_pin = Column(Integer)
    has_battery = Column(Boolean, default=False)
    battery_mah = Column(Integer)
    powered_by = Column(String)
    ip_rating = Column(String)
    coverage_radius_m = Column(Integer)
    wifi_factor = Column(Float)
    fusion_weight = Column(Float)
    firmware = Column(String)
    cost_eur = Column(Float)
    notes = Column(Text)
    critical_note = Column(Text)
    installed_at = Column(TIMESTAMP(timezone=True))
    installed_by = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    is_active = Column(Boolean, server_default=text("true"))


class SensorHealth(Base):
    __tablename__ = "sensor_health"

    sensor_id = Column(String, ForeignKey("sensors.id", ondelete="CASCADE"), primary_key=True)
    last_seen = Column(TIMESTAMP(timezone=True))
    last_rssi_dbm = Column(Integer)
    last_uptime_s = Column(Integer)
    battery_pct = Column(Integer)
    firmware_ver = Column(String)
    events_today = Column(Integer, server_default=text("0"))
    status = Column(String, server_default=text("'unknown'"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class MaintenanceLog(Base):
    __tablename__ = "maintenance_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sensor_id = Column(String, ForeignKey("sensors.id", ondelete="CASCADE"))
    action = Column(String, nullable=False)
    result = Column(String)
    notes = Column(Text)
    performed_by = Column(String)
    performed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class TerminalLog(Base):
    __tablename__ = "terminal_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String)
    command = Column(String, nullable=False)
    output = Column(Text)
    exit_code = Column(Integer)
    executed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
