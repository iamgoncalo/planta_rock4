from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api/v1", tags=["firmware"])

_FW_DIR = Path(__file__).resolve().parents[2] / "firmware" / "rir2026"


def _safe(name: str) -> Path:
    if not name.endswith(".ino") or "/" in name or ".." in name:
        raise HTTPException(status_code=400, detail="nome invalido")
    p = (_FW_DIR / name).resolve()
    if not str(p).startswith(str(_FW_DIR.resolve())) or not p.exists():
        raise HTTPException(status_code=404, detail="ino nao encontrado")
    return p


@router.get("/firmware")
async def list_firmware():
    if not _FW_DIR.exists():
        return {"files": [], "total": 0}
    files = sorted(p.name for p in _FW_DIR.glob("*.ino") if not p.name.startswith("_"))
    return {"files": files, "total": len(files)}


@router.get("/firmware/{name}", response_class=PlainTextResponse)
async def get_firmware(name: str):
    return _safe(name).read_text(encoding="utf-8")
