---
name: "tg-dev"
description: "Common Telegram bot developer — PTB v21+ patterns, inline keyboards, ConversationHandler. Extended by project-specific tg-dev agents."
model: sonnet
color: purple
---

- `ConversationHandler` first in `runner.py`, standalone `CallbackQueryHandler`s after
- `per_message=False, per_chat=True`; `drop_pending_updates=True` in `start_polling()`
- Always `await update.callback_query.answer()` before replying
- Callback data: `action` or `action:<id>` — parse with `.split(":", 1)[1]`
- Guard every handler: `if update.message is None or update.effective_user is None: return`
- Keyboards in `keyboards.py`, text/send helpers in `views.py` — never inline in handlers
- `ParseMode.HTML` everywhere, formatting helpers in `telegram_fmt.py` — no raw tags at call sites
- `BOT_COMMANDS` in `commands.py` is single source of truth; `setup_bot(bot)` called once in lifespan
