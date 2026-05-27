from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    ts: float


class ChatContext(BaseModel):
    live_payload: Optional[Any] = None
    active_show: Optional[Any] = None
    route_decision: Optional[Any] = None


class ChatRequest(BaseModel):
    message: str
    context: Optional[ChatContext] = None


class ChatResponse(BaseModel):
    reply: str
    grounded: bool
    live_data_available: bool
    ts: float
