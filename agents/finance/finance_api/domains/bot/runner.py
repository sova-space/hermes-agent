"""Build and run the Telegram finance bot."""

from telegram import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeChat,
    MenuButtonWebApp,
    WebAppInfo,
)
from telegram.ext import Application, CommandHandler

from finance_api.core.config import get_settings
from finance_api.domains.bot.handlers import balance, cmd_finance_app, sync

_COMMANDS = [
    BotCommand("finance_app", "Open Finance Mini App"),
    BotCommand("balance", "Show account balances"),
    BotCommand("sync", "Sync Monobank"),
]


async def _post_init(app: Application) -> None:
    """Register commands and Mini App button with Telegram on every startup."""
    settings = get_settings()
    await app.bot.set_my_commands(_COMMANDS)
    await app.bot.set_my_commands(_COMMANDS, scope=BotCommandScopeAllGroupChats())
    await app.bot.set_my_commands(
        _COMMANDS, scope=BotCommandScopeChat(chat_id=settings.telegram_chat_id)
    )
    if settings.mini_app_url:
        await app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Open Finance",
                web_app=WebAppInfo(url=settings.mini_app_url),
            )
        )


def create_bot(token: str) -> Application:
    """Create the bot Application with all command handlers registered."""
    app = Application.builder().token(token).post_init(_post_init).build()
    app.add_handler(CommandHandler("finance_app", cmd_finance_app))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("sync", sync))
    return app
