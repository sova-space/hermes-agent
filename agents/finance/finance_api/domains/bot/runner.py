"""Build and run the Telegram finance bot."""

from telegram.ext import Application, CommandHandler

from finance_api.domains.bot.handlers import balance, cmd_start, sync


def create_bot(token: str) -> Application:
    """Create the bot Application with all command handlers registered."""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("sync", sync))
    return app
