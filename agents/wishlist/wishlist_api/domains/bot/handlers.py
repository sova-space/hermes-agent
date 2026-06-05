"""Telegram bot handlers for the wishlist bot."""

import uuid

import structlog
from sqlmodel import select as sql_select
from telegram import ForceReply, Update
from telegram.ext import ContextTypes, ConversationHandler

from wishlist_api.core.config import get_settings
from wishlist_api.core.db.engine import get_session
from wishlist_api.domains.bot.keyboards import (
    friend_view_keyboard,
    friend_view_text,
    main_menu_keyboard,
    main_menu_text,
)
from wishlist_api.domains.bot.views import (
    get_item_counts,
    parse_item_text,
    send_list_view,
    send_main_menu,
)
from wishlist_api.domains.wish import queries
from wishlist_api.domains.wish.models import WishItem

log = structlog.get_logger(__name__)

AWAITING_LIST_NAME = "AWAITING_LIST_NAME"
AWAITING_ITEM = "AWAITING_ITEM"


async def handle_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int | None:
    """Entry point: /start [view_<token>]."""
    if update.message is None or update.effective_user is None:
        return None

    user = update.effective_user
    args: list[str] = context.args or []

    if args and args[0].startswith("view_"):
        token = args[0][len("view_") :]
        return await _show_friend_view(update, context, token)

    with next(get_session()) as session:
        queries.upsert_user(session, user.id, user.first_name)
        wishlists = queries.list_wishlists(session, user.id)

    counts = get_item_counts(wishlists)
    text = main_menu_text(wishlists, counts)
    keyboard = main_menu_keyboard(wishlists)
    await update.message.reply_text(text, reply_markup=keyboard)
    return ConversationHandler.END


async def _show_friend_view(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    token: str,
) -> int | None:
    """Show the friend view for a shared wishlist token."""
    if update.message is None or update.effective_user is None:
        return None

    with next(get_session()) as session:
        wishlist = queries.get_wishlist_by_token(session, token)
        if wishlist is None:
            await update.message.reply_text(
                "This wishlist link is invalid or has been deleted."
            )
            return ConversationHandler.END
        items = queries.list_items(session, uuid.UUID(wishlist["id"]))

    viewer_id = update.effective_user.id
    text = friend_view_text(wishlist, items)
    keyboard = friend_view_keyboard(items, viewer_id)
    await update.message.reply_text(text, reply_markup=keyboard)
    return ConversationHandler.END


# ── Callback handlers ─────────────────────────────────────────────────────────


async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'menu' callback — show main menu."""
    if update.callback_query:
        await update.callback_query.answer()
    await send_main_menu(update, context)


async def callback_open(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'open:<wishlist_id>' callback — show list view."""
    if update.callback_query is None:
        return
    await update.callback_query.answer()
    wishlist_id = uuid.UUID(update.callback_query.data.split(":", 1)[1])
    await send_list_view(update, context, wishlist_id)


async def callback_newlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Handle 'newlist' callback — ask for wishlist name."""
    if update.callback_query is None or update.callback_query.message is None:
        return ConversationHandler.END  # type: ignore[return-value]
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "Enter a name for your new wishlist:",
        reply_markup=ForceReply(selective=True),
    )
    return AWAITING_LIST_NAME


async def callback_additem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Handle 'additem:<wishlist_id>' callback — ask for item text."""
    if update.callback_query is None or update.callback_query.message is None:
        return ConversationHandler.END  # type: ignore[return-value]
    await update.callback_query.answer()
    wishlist_id = update.callback_query.data.split(":", 1)[1]
    context.user_data["adding_to_wishlist"] = wishlist_id  # type: ignore[index]
    await update.callback_query.message.reply_text(
        "Send the item (title, optional ~price, optional URL):\n"
        "Example: Perfume ~$120 https://example.com",
        reply_markup=ForceReply(selective=True),
    )
    return AWAITING_ITEM


async def callback_share(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'share:<wishlist_id>' callback — send share link."""
    if update.callback_query is None or update.callback_query.message is None:
        return
    await update.callback_query.answer()
    wishlist_id = uuid.UUID(update.callback_query.data.split(":", 1)[1])

    with next(get_session()) as session:
        wishlist = queries.get_wishlist_by_id(session, wishlist_id)
    if wishlist is None:
        return

    settings = get_settings()
    link = f"https://t.me/{settings.bot_username}?start=view_{wishlist['share_token']}"
    await update.callback_query.message.reply_text(
        f"Share this link with friends:\n{link}"
    )


async def callback_dellist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'dellist:<wishlist_id>' callback — delete wishlist."""
    if update.callback_query is None:
        return
    await update.callback_query.answer()
    wishlist_id = uuid.UUID(update.callback_query.data.split(":", 1)[1])

    with next(get_session()) as session:
        queries.delete_wishlist(session, wishlist_id)

    await send_main_menu(update, context)


async def callback_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'remove:<item_id>' callback — remove item and refresh list."""
    if update.callback_query is None:
        return
    await update.callback_query.answer()
    item_id = uuid.UUID(update.callback_query.data.split(":", 1)[1])

    with next(get_session()) as session:
        wish_item = session.exec(
            sql_select(WishItem).where(WishItem.id == item_id)
        ).first()
        wishlist_id = wish_item.wishlist_id if wish_item else None
        queries.remove_item(session, item_id)

    if wishlist_id:
        await send_list_view(update, context, wishlist_id)
    else:
        await send_main_menu(update, context)


async def callback_claim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'claim:<item_id>' callback — claim item and refresh friend view."""
    if update.callback_query is None or update.effective_user is None:
        return
    await update.callback_query.answer()
    item_id = uuid.UUID(update.callback_query.data.split(":", 1)[1])
    user = update.effective_user

    with next(get_session()) as session:
        result = queries.claim_item(session, item_id, user.first_name, user.id)
        if result is None:
            return
        wishlist_id = uuid.UUID(result["wishlist_id"])
        wishlist = queries.get_wishlist_by_id(session, wishlist_id)
        items = queries.list_items(session, wishlist_id)

    if wishlist is None or update.callback_query.message is None:
        return

    text = friend_view_text(wishlist, items)
    keyboard = friend_view_keyboard(items, user.id)
    await update.callback_query.message.edit_text(text, reply_markup=keyboard)


async def callback_unclaim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'unclaim:<item_id>' callback — unclaim item if caller is the claimer."""
    if update.callback_query is None or update.effective_user is None:
        return
    await update.callback_query.answer()
    item_id = uuid.UUID(update.callback_query.data.split(":", 1)[1])
    user = update.effective_user

    with next(get_session()) as session:
        result = queries.unclaim_item(session, item_id, user.id)
        if result is None:
            await update.callback_query.answer(
                "You did not claim this item.", show_alert=True
            )
            return
        wishlist_id = uuid.UUID(result["wishlist_id"])
        wishlist = queries.get_wishlist_by_id(session, wishlist_id)
        items = queries.list_items(session, wishlist_id)

    if wishlist is None or update.callback_query.message is None:
        return

    text = friend_view_text(wishlist, items)
    keyboard = friend_view_keyboard(items, user.id)
    await update.callback_query.message.edit_text(text, reply_markup=keyboard)


# ── Conversation state handlers ───────────────────────────────────────────────


async def receive_list_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """AWAITING_LIST_NAME state: create wishlist with given title."""
    if update.message is None or update.effective_user is None:
        return ConversationHandler.END

    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text("Name cannot be empty. Try again:")
        return AWAITING_LIST_NAME  # type: ignore[return-value]

    user = update.effective_user
    with next(get_session()) as session:
        wishlist = queries.create_wishlist(session, user.id, title)

    await send_list_view(update, context, uuid.UUID(wishlist["id"]))
    return ConversationHandler.END


async def receive_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """AWAITING_ITEM state: parse and add an item to the active wishlist."""
    if update.message is None or context.user_data is None:
        return ConversationHandler.END

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Item text cannot be empty. Try again:")
        return AWAITING_ITEM  # type: ignore[return-value]

    wishlist_id_str: str | None = context.user_data.get("adding_to_wishlist")
    if not wishlist_id_str:
        await update.message.reply_text("Something went wrong. Please start over.")
        return ConversationHandler.END

    wishlist_id = uuid.UUID(wishlist_id_str)
    title, price, url = parse_item_text(text)

    if not title:
        await update.message.reply_text(
            "Could not parse a title. Please include item name:"
        )
        return AWAITING_ITEM  # type: ignore[return-value]

    with next(get_session()) as session:
        queries.add_item(session, wishlist_id, title, price, url)

    context.user_data.pop("adding_to_wishlist", None)
    await send_list_view(update, context, wishlist_id)
    return ConversationHandler.END
