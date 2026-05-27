from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel

AlertSeverity = Literal["info", "warning", "critical"]


class Alert(BaseModel):
    alert_id: str
    severity: AlertSeverity
    section_id: Optional[str] = None
    message: str
    ts: float
    acknowledged: bool = False
