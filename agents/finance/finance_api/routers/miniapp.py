"""Mini App HTML endpoint."""

import os

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@router.get("/miniapp", include_in_schema=False)
async def miniapp() -> FileResponse:
    """Serve the Telegram Mini App HTML shell."""
    path = os.path.join(_STATIC_DIR, "miniapp.html")
    return FileResponse(path, media_type="text/html")
