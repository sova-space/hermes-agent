"""Telegram command handlers for the finance bot."""

import asyncio

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.error import BadRequest
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
    get_hidden_account_balances,
    get_income_summary,
    get_sync_health,
    get_visible_account_count,
)
from finance_api.domains.sync.monobank import run_sync

log = structlog.get_logger(__name__)

SYNC_CALLBACK = "sync"
INCOME_CALLBACK = "income"
SKIPPED_CALLBACK = "skipped"
BALANCE_CALLBACK = "balance_cb"

_MSG_NOT_MODIFIED = "message is not modified"


def _balance_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Balance", callback_data=BALANCE_CALLBACK),
            InlineKeyboardButton("💰 Income", callback_data=INCOME_CALLBACK),
            InlineKeyboardButton("👁 Skipped", callback_data=SKIPPED_CALLBACK),
        ],
        [
            InlineKeyboardButton("🔄 Sync", callback_data=SYNC_CALLBACK),
            InlineKeyboardButton("📊 Finance", url=settings.mini_app_url),
        ],
    ])


def _thread_id(message) -> int | None:
    """Return the forum topic thread ID for a message, or None outside topics."""
    return getattr(message, "message_thread_id", None)


async def _edit(query, text: str, **kwargs) -> None:
    """Edit the message in place; silently ignore if content is unchanged."""
    try:
        await query.edit_message_text(text, **kwargs)
    except BadRequest as e:
        if _MSG_NOT_MODIFIED not in str(e).lower():
            raise


_MONO_RATE_LIMIT_S = 62  # Monobank allows one request per 62 s per token
_sync_running = False


async def _sync_then_edit(message: Message) -> None:
    """Background task: run sync and edit message with the final status."""
    global _sync_running
    try:
        await asyncio.to_thread(run_sync)
        status = await asyncio.to_thread(get_sync_health)
        try:
            await message.edit_text(
                format_sync_status(status),
                parse_mode=PARSE_MODE,
                reply_markup=_balance_keyboard(),
            )
        except BadRequest as e:
            if _MSG_NOT_MODIFIED not in str(e).lower():
                raise
    finally:
        _sync_running = False


async def _do_sync(message: Message) -> None:
    """For /sync command — reply with status message, edit it when done."""
    n = await asyncio.to_thread(get_visible_account_count)
    est_min = max(1, round(n * _MONO_RATE_LIMIT_S / 60))
    sent = await message.reply_text(
        f"🔄 Syncing…  ~{est_min} min", parse_mode=PARSE_MODE
    )
    asyncio.create_task(_sync_then_edit(sent))  # noqa: RUF006


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
        and _thread_id(update.message) == settings.telegram_finance_topic_id
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
        await ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=_thread_id(update.message),
            text=format_balance(accounts),
            parse_mode=PARSE_MODE,
            reply_markup=_balance_keyboard(),
        )
    except Exception as e:
        log.error("balance_failed", error=str(e))
        await ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=_thread_id(update.message),
            text=f"❌ Error: {code(e)}",
            parse_mode=PARSE_MODE,
        )


async def callback_balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 💳 Balance button — edit message with fresh balance."""
    query = update.callback_query
    await query.answer()
    try:
        accounts = await asyncio.to_thread(get_account_balances)
        await _edit(
            query,
            format_balance(accounts),
            parse_mode=PARSE_MODE,
            reply_markup=_balance_keyboard(),
        )
    except Exception as e:
        log.error("balance_callback_failed", error=str(e))
        await _edit(query, f"❌ Error: {code(e)}", parse_mode=PARSE_MODE)


async def callback_income(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 💰 Income button — edit message with income/spending summary."""
    query = update.callback_query
    await query.answer()
    try:
        income = await asyncio.to_thread(get_income_summary)
        text = format_income_summary(income) or "No income data for this month yet."
        await _edit(
            query, text, parse_mode=PARSE_MODE, reply_markup=_balance_keyboard()
        )
    except Exception as e:
        log.error("income_callback_failed", error=str(e))
        await _edit(query, f"❌ Error: {code(e)}", parse_mode=PARSE_MODE)


async def callback_skipped(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 👁 Skipped button — edit message with hidden accounts."""
    query = update.callback_query
    await query.answer()
    try:
        accounts = await asyncio.to_thread(get_hidden_account_balances)
        text = format_balance(accounts) if accounts else "No skipped accounts."
        await _edit(
            query, text, parse_mode=PARSE_MODE, reply_markup=_balance_keyboard()
        )
    except Exception as e:
        log.error("skipped_callback_failed", error=str(e))
        await _edit(query, f"❌ Error: {code(e)}", parse_mode=PARSE_MODE)


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
    """Handle 🔄 Sync button — edit message to syncing state, update when done."""
    global _sync_running
    query = update.callback_query
    await query.answer()
    n = await asyncio.to_thread(get_visible_account_count)
    est_min = max(1, round(n * _MONO_RATE_LIMIT_S / 60))
    if _sync_running:
        # Sync already running — just show progress, don't start a second one
        await _edit(
            query,
            f"🔄 Syncing…  ~{est_min} min",
            parse_mode=PARSE_MODE,
            reply_markup=_balance_keyboard(),
        )
        return
    _sync_running = True
    try:
        await _edit(
            query,
            f"🔄 Syncing…  ~{est_min} min",
            parse_mode=PARSE_MODE,
            reply_markup=_balance_keyboard(),
        )
        asyncio.create_task(_sync_then_edit(query.message))  # noqa: RUF006
    except Exception as e:
        _sync_running = False
        log.error("sync_callback_failed", error=str(e))
        await _edit(query, f"❌ Sync failed: {code(e)}", parse_mode=PARSE_MODE)
