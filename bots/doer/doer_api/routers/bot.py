"""Hermes ecosystem discovery endpoint."""

from fastapi import APIRouter

router = APIRouter()

BOT_COMMANDS: list[dict] = [
    {"command": "project", "description": "Pick active project for Doer (Finance / Wishlist / Hermes)"},
    {"command": "do", "description": "Run a task on the active project via Doer"},
]


@router.get("/bot/commands", include_in_schema=False)
async def bot_commands() -> list[dict]:
    """Return registered bot commands. Hermes fetches this for command ownership."""
    return BOT_COMMANDS
