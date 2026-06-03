"""Telegram command handlers for the finance bot."""

import asyncio

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from finance_api.bot.telegram_fmt import PARSE_MODE, code
from finance_api.core.config import settings
from finance_api.domains.bot.formatter import (
    format_balance,
    format_income_summary,
    format_sync_status,
)
from finance_api.domains.insights.queries import (
    get_account_balances,
    get_income_summary,
    get_sync_health,
)
from finance_api.domains.sync.monobank import run_sync

log = structlog.get_logger(__name__)

SYNC_CALLBACK = "sync"
INCOME_CALLBACK = "income"


def _balance_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Income", callback_data=INCOME_CALLBACK),
            InlineKeyboardButton("🔄 Sync", callback_data=SYNC_CALLBACK),
            InlineKeyboardButton("📊 Finance", url=settings.mini_app_url),
        ]
    ])


async def _do_sync(message: Message) -> None:
    """Fire sync in background and send status replies to message."""
    await message.reply_text("🔄 Syncing…", parse_mode=PARSE_MODE)
    # Run sync in background without blocking the handler — full sync takes
    # several minutes due to Monobank rate limiting (62 s per account).
    asyncio.get_running_loop().run_in_executor(None, run_sync)
    await asyncio.sleep(0.5)
    status = await asyncio.to_thread(get_sync_health)
    await message.reply_text(format_sync_status(status), parse_mode=PARSE_MODE)


async def cmd_finance_app(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /finance_app command — open the Mini App."""
    url = settings.mini_app_url
    # Use a plain URL button everywhere — InlineKeyboardButton.web_app requires
    # the domain to be approved in BotFather, which fails with Button_type_invalid
    # until that is configured.
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Open Finance", url=url)]])
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
        accounts = await asyncio.to_thread(get_account_balances)
        await update.message.reply_text(
            format_balance(accounts),
            parse_mode=PARSE_MODE,
            reply_markup=_balance_keyboard(),
        )
    except Exception as e:
        log.error("balance_failed", error=str(e))
        await update.message.reply_text(f"❌ Error: {code(e)}", parse_mode=PARSE_MODE)


async def callback_income(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 💰 Income button — send income vs spending summary."""
    query = update.callback_query
    await query.answer()
    try:
        income = await asyncio.to_thread(get_income_summary)
        text = format_income_summary(income) or "No income data for this month yet."
        await query.message.reply_text(text, parse_mode=PARSE_MODE)
    except Exception as e:
        log.error("income_callback_failed", error=str(e))
        await query.message.reply_text(f"❌ Error: {code(e)}", parse_mode=PARSE_MODE)


async def sync(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sync command."""
    try:
        await _do_sync(update.message)
    except Exception as e:
        log.error("sync_failed", error=str(e))
        await update.message.reply_text(
            f"❌ Sync failed: {code(e)}", parse_mode=PARSE_MODE
        )


async def callback_sync(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 🔄 Sync inline button press."""
    query = update.callback_query
    await query.answer()
    try:
        await _do_sync(query.message)
    except Exception as e:
        log.error("sync_callback_failed", error=str(e))
        await query.message.reply_text(
            f"❌ Sync failed: {code(e)}", parse_mode=PARSE_MODE
        )
