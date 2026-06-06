"""Hermes ecosystem discovery endpoint."""

from fastapi import APIRouter

router = APIRouter()

# Doer owns no Telegram commands — Hermes routes /do_* via a skill.
BOT_COMMANDS: list[dict] = []


@router.get("/bot/commands", include_in_schema=False)
async def bot_commands() -> list[dict]:
    """Return registered bot commands. Hermes fetches this for command ownership."""
    return BOT_COMMANDS
