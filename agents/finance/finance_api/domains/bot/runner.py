"""Build the Telegram bot application."""

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from finance_api.domains.bot.commands import BOT_COMMANDS
from finance_api.domains.bot.handlers import (
    SYNC_CALLBACK,
    balance,
    callback_sync,
    cmd_finance_app,
    sync,
)


def create_bot(token: str) -> Application:
    """Create the bot Application with all command handlers registered."""
    app = Application.builder().token(token).build()
    handler_map = {
        "finance_app": cmd_finance_app,
        "balance": balance,
        "sync": sync,
    }
    for command in BOT_COMMANDS:
        if handler := handler_map.get(command.command):
            app.add_handler(CommandHandler(command.command, handler))
    app.add_handler(CallbackQueryHandler(callback_sync, pattern=f"^{SYNC_CALLBACK}$"))
    return app
