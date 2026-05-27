from __future__ import annotations
from fastapi import APIRouter
from app.models.chat import ChatRequest, ChatResponse
from app.services.state import get_live_payload, get_active_show
from app.services.routing import compute_route
from app.services import chat as chat_service

router = APIRouter(prefix="/api/v1", tags=["chat"])

# Default venue centre for chat routing context
_DEFAULT_LAT = 38.782
_DEFAULT_LON = -9.093


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    """Answer a natural language question using live WC data."""
    try:
        payload = get_live_payload()
    except Exception:
        payload = None

    route = None
    if payload is not None:
        try:
            active_show = get_active_show()
            route = compute_route(payload.sections, _DEFAULT_LAT, _DEFAULT_LON, active_show)
        except Exception:
            pass

    return chat_service.answer_chat(body.message, payload, route)
