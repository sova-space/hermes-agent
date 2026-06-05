"""Build the Telegram bot application."""

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from wishlist_api.domains.bot.handlers import (
    AWAITING_ITEM,
    AWAITING_LIST_NAME,
    callback_additem,
    callback_claim,
    callback_dellist,
    callback_menu,
    callback_newlist,
    callback_open,
    callback_remove,
    callback_share,
    callback_unclaim,
    handle_start,
    receive_item,
    receive_list_name,
)


def create_bot(token: str) -> Application:
    """Create the bot Application with all handlers registered."""
    app = Application.builder().token(token).build()

    # ConversationHandler must be registered first.
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", handle_start),
            CallbackQueryHandler(callback_newlist, pattern="^newlist$"),
            CallbackQueryHandler(callback_additem, pattern="^additem:"),
        ],
        states={
            AWAITING_LIST_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_list_name)
            ],
            AWAITING_ITEM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_item)
            ],
        },
        fallbacks=[CommandHandler("start", handle_start)],
        per_message=False,
        per_chat=True,
    )
    app.add_handler(conv_handler)

    # Standalone callback handlers (anchored patterns).
    app.add_handler(CallbackQueryHandler(callback_menu, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(callback_open, pattern="^open:"))
    app.add_handler(CallbackQueryHandler(callback_share, pattern="^share:"))
    app.add_handler(CallbackQueryHandler(callback_dellist, pattern="^dellist:"))
    app.add_handler(CallbackQueryHandler(callback_remove, pattern="^remove:"))
    app.add_handler(CallbackQueryHandler(callback_claim, pattern="^claim:"))
    app.add_handler(CallbackQueryHandler(callback_unclaim, pattern="^unclaim:"))

    return app
