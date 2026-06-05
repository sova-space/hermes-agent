"""Bot commands endpoint — consumed by Hermes to stay in sync."""

from fastapi import APIRouter

from wishlist_api.domains.bot.commands import BOT_COMMANDS

router = APIRouter()


@router.get("/bot/commands", include_in_schema=False)
async def bot_commands() -> list[dict]:
    """Return registered bot commands. Hermes fetches this to stay in sync."""
    return [{"command": c.command, "description": c.description} for c in BOT_COMMANDS]
