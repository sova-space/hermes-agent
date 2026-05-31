"""Telegram command handlers for the finance bot."""

import asyncio

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes

from finance_api.core.config import settings
from finance_api.domains.bot.formatter import format_balance, format_sync_status
from finance_api.domains.insights.queries import get_account_balances, get_sync_health
from finance_api.domains.sync.monobank import run_sync

log = structlog.get_logger(__name__)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command — open the Mini App."""
    if not settings.mini_app_url:
        await update.message.reply_text("Mini App not configured yet.")
        return
    url = settings.mini_app_url
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Open Finance", web_app=WebAppInfo(url=url))]]
    )
    text = "💰 Hermes Finance"
    in_finance_topic = (
        update.effective_chat.id == settings.telegram_chat_id
        and getattr(update.message, "message_thread_id", None)
        == settings.telegram_finance_topic_id
    )
    if in_finance_topic or update.effective_chat.type == "private":
        await update.message.reply_text(text, reply_markup=keyboard)
    else:
        await ctx.bot.send_message(
            chat_id=settings.telegram_chat_id,
            message_thread_id=settings.telegram_finance_topic_id,
            text=text,
            reply_markup=keyboard,
        )


async def balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /balance command."""
    try:
        accounts = get_account_balances()
        await update.message.reply_html(format_balance(accounts))
    except Exception as e:
        log.error("balance_failed", error=str(e))
        await update.message.reply_html(f"❌ Error: <code>{e}</code>")


async def sync(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sync command — trigger Monobank sync in background."""
    try:
        await update.message.reply_html("🔄 Syncing…")
        await asyncio.to_thread(run_sync)
        status = get_sync_health()
        await update.message.reply_html(format_sync_status(status))
    except Exception as e:
        log.error("sync_failed", error=str(e))
        await update.message.reply_html(f"❌ Sync failed: <code>{e}</code>")
