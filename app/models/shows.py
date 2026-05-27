from __future__ import annotations
from pydantic import BaseModel


class Show(BaseModel):
    show_id: str
    name: str
    stage: str
    start_iso: str
    end_iso: str
    headliner: bool
    expected_surge_pct: float


class ShowImpact(BaseModel):
    show_id: str
    affected_sections: list[str]
    surge_penalty_min: float
