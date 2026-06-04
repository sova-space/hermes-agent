"""Build the Telegram bot application."""

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from finance_api.domains.bot.commands import BOT_COMMANDS
from finance_api.domains.bot.handlers import (
    BALANCE_CALLBACK,
    INCOME_CALLBACK,
    SKIPPED_CALLBACK,
    SPENDING_CALLBACK,
    SYNC_CALLBACK,
    balance,
    callback_balance,
    callback_income,
    callback_skipped,
    callback_spending,
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
    app.add_handler(
        CallbackQueryHandler(callback_balance, pattern=f"^{BALANCE_CALLBACK}$")
    )
    app.add_handler(CallbackQueryHandler(callback_sync, pattern=f"^{SYNC_CALLBACK}$"))
    app.add_handler(
        CallbackQueryHandler(callback_income, pattern=f"^{INCOME_CALLBACK}$")
    )
    app.add_handler(
        CallbackQueryHandler(callback_skipped, pattern=f"^{SKIPPED_CALLBACK}$")
    )
    app.add_handler(
        CallbackQueryHandler(callback_spending, pattern=f"^{SPENDING_CALLBACK}$")
    )
    return app
