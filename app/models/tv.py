from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class TVScreenState(BaseModel):
    screen_id: str
    recommended_section: str
    direction: str
    walk_time_min: float
    queue_wait_min: float
    alternative_section: Optional[str] = None
    avoid_list: list[str]
    critical_override: bool
    last_update_ts: float
    any_simulated: bool
