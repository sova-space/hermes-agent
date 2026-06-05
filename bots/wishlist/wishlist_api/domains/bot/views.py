"""Message dispatchers — fetch data and render/send menu or list views."""

import re
import uuid
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from wishlist_api.core.db.engine import get_session
from wishlist_api.domains.bot.keyboards import (
    friend_view_keyboard,
    friend_view_text,
    list_view_keyboard,
    list_view_text,
    main_menu_keyboard,
    main_menu_text,
)
from wishlist_api.domains.wish import queries

_URL_RE = re.compile(r"https?://\S+")
_PRICE_RE = re.compile(r"~\S+")


def get_item_counts(wishlists: list[dict[str, Any]]) -> dict[str, int]:
    """Return a map of wishlist_id → item count."""
    counts: dict[str, int] = {}
    with next(get_session()) as session:
        for wl in wishlists:
            counts[wl["id"]] = len(queries.list_items(session, uuid.UUID(wl["id"])))
    return counts


def parse_item_text(text: str) -> tuple[str, str | None, str | None]:
    """Parse user item text into (title, price, url)."""
    url_match = _URL_RE.search(text)
    url = url_match.group(0) if url_match else None
    text_no_url = _URL_RE.sub("", text).strip()

    price_match = _PRICE_RE.search(text_no_url)
    price = price_match.group(0) if price_match else None
    title = _PRICE_RE.sub("", text_no_url).strip()

    return title, price, url


async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Edit or send the main menu for the current user."""
    if update.effective_user is None:
        return

    user_id = update.effective_user.id
    with next(get_session()) as session:
        wishlists = queries.list_wishlists(session, user_id)

    counts = get_item_counts(wishlists)
    text = main_menu_text(wishlists, counts)
    keyboard = main_menu_keyboard(wishlists)

    if update.callback_query and update.callback_query.message:
        await update.callback_query.message.edit_text(text, reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text, reply_markup=keyboard)


async def send_list_view(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    wishlist_id: uuid.UUID,
) -> None:
    """Edit or send the list view for a wishlist."""
    with next(get_session()) as session:
        wishlist = queries.get_wishlist_by_id(session, wishlist_id)
        if wishlist is None:
            return
        items = queries.list_items(session, wishlist_id)

    text = list_view_text(wishlist, items)
    keyboard = list_view_keyboard(str(wishlist_id))

    # Append per-item remove buttons below the main keyboard rows.
    remove_rows = [
        [InlineKeyboardButton(f"Remove #{i}", callback_data=f"remove:{item['id']}")]
        for i, item in enumerate(items, start=1)
    ]
    full_keyboard = InlineKeyboardMarkup(keyboard.inline_keyboard + remove_rows)

    if update.callback_query and update.callback_query.message:
        await update.callback_query.message.edit_text(text, reply_markup=full_keyboard)
    elif update.message:
        await update.message.reply_text(text, reply_markup=full_keyboard)


async def send_friend_view(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    wishlist_id: uuid.UUID,
    viewer_telegram_id: int,
) -> None:
    """Edit or send the friend view for a wishlist."""
    with next(get_session()) as session:
        wishlist = queries.get_wishlist_by_id(session, wishlist_id)
        if wishlist is None:
            return
        items = queries.list_items(session, wishlist_id)

    text = friend_view_text(wishlist, items)
    keyboard = friend_view_keyboard(items, viewer_telegram_id)

    if update.callback_query and update.callback_query.message:
        await update.callback_query.message.edit_text(text, reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
