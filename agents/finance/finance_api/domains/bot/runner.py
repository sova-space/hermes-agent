"""Build and run the Telegram finance bot."""

from telegram import BotCommand, MenuButtonWebApp, WebAppInfo
from telegram.ext import Application, CommandHandler

from finance_api.core.config import get_settings
from finance_api.domains.bot.handlers import balance, cmd_start, sync

_COMMANDS = [
    BotCommand("start", "Open Finance Mini App"),
    BotCommand("balance", "Show account balances"),
    BotCommand("sync", "Sync Monobank"),
]


async def _post_init(app: Application) -> None:
    """Register commands and Mini App button with Telegram on every startup."""
    await app.bot.set_my_commands(_COMMANDS)
    settings = get_settings()
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
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("sync", sync))
    return app
