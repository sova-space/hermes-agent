"""Mini App HTML endpoint and bot trigger."""

import os

from fastapi import APIRouter
from fastapi.responses import FileResponse

from finance_api.domains.bot.commands import BOT_COMMANDS
from finance_api.domains.bot.notifications import send_finance_app_button

router = APIRouter()

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@router.get("/miniapp", include_in_schema=False)
async def miniapp() -> FileResponse:
    """Serve the Telegram Mini App HTML shell."""
    path = os.path.join(_STATIC_DIR, "miniapp.html")
    return FileResponse(path, media_type="text/html")


@router.post("/bot/open", include_in_schema=False)
async def bot_open() -> dict:
    """Send the Mini App button to the #finance topic. Called by Hermes skill."""
    send_finance_app_button()
    return {"ok": True}


@router.get("/bot/commands", include_in_schema=False)
async def bot_commands() -> list[dict]:
    """Return registered bot commands. Hermes fetches this to stay in sync."""
    return [{"command": c.command, "description": c.description} for c in BOT_COMMANDS]
