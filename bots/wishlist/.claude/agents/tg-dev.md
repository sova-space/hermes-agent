---
name: "wishlist-tg-dev"
description: "Telegram developer for bots/wishlist/. Extends common tg-dev agent."
model: sonnet
color: purple
---

Extends: read `/Users/nkhimin/Projects/personal/hermes-agent/.claude/agents/common/tg-dev.md` first.

**Share link:** `f"https://t.me/{settings.bot_username}?start=view_{wishlist['share_token']}"` — deep link opens friend view, no auth.

**File ownership:** `keyboards.py` builds all `InlineKeyboardMarkup` · `views.py` owns all text + `send_main_menu()` / `send_list_view()` · `handlers.py` calls them, never builds markup inline.
