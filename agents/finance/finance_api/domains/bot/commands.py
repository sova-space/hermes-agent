"""Bot startup configuration — commands and any future setup steps.

To add a new startup action: add an async _setup_* function and call it in setup_bot().
"""

import structlog
from telegram import (
    Bot,
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeChat,
)

from finance_api.core.config import get_settings

log = structlog.get_logger(__name__)

BOT_COMMANDS: list[BotCommand] = [
    BotCommand("finance_app", "Open Finance Mini App"),
    BotCommand("balance", "Show account balances"),
    BotCommand("sync", "Sync Monobank"),
]


async def _register_commands(bot: Bot) -> None:
    settings = get_settings()
    await bot.set_my_commands(BOT_COMMANDS)
    await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeAllGroupChats())
    await bot.set_my_commands(
        BOT_COMMANDS,
        scope=BotCommandScopeChat(chat_id=settings.telegram_chat_id),
    )
    log.info("bot_commands_registered", count=len(BOT_COMMANDS))


async def setup_bot(bot: Bot) -> None:
    """Run all bot startup steps. Add new steps here."""
    await _register_commands(bot)
