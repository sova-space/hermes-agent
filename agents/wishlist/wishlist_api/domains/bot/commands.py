"""Bot startup configuration — commands and startup steps.

To add a new startup action: add an async _setup_* function and call it in setup_bot().
"""

import structlog
from telegram import Bot, BotCommand

log = structlog.get_logger(__name__)

BOT_COMMANDS: list[BotCommand] = [
    BotCommand("start", "Open Wishlist Bot"),
]


async def setup_bot(bot: Bot) -> None:
    """Run all bot startup steps."""
    await bot.set_my_commands(BOT_COMMANDS)
    log.info("bot_commands_registered", count=len(BOT_COMMANDS))
