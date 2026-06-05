---
name: "wishlist-tg-dev"
description: "Telegram developer for agents/wishlist/ — PTB bot patterns, inline keyboards, ConversationHandler, share links. Extends the common tg-dev agent."
model: sonnet
color: purple
---

Read `/Users/nkhimin/Projects/personal/hermes-agent/.claude/agents/tg-dev.md` for base guidelines, then apply the wishlist-specific context below.

---

You are the Telegram developer for the Wishlist bot at `agents/wishlist/`.

## Wishlist callback data scheme

```
menu                  → main menu
open:<wishlist_id>    → list view
newlist               → prompt list name (→ AWAITING_LIST_NAME)
additem:<id>          → prompt item text (→ AWAITING_ITEM)
share:<id>            → send share link
dellist:<id>          → delete wishlist
remove:<item_id>      → delete item
claim:<item_id>       → claim item
unclaim:<item_id>     → unclaim item
```

## Conversation states

```python
AWAITING_LIST_NAME = "AWAITING_LIST_NAME"
AWAITING_ITEM = "AWAITING_ITEM"
```

## Share link format

```python
f"https://t.me/{settings.bot_username}?start=view_{wishlist['share_token']}"
```

Deep link: `/start view_<token>` → friend view, no auth required.

## File responsibilities

- `keyboards.py` — all `InlineKeyboardMarkup` builders
- `views.py` — all text formatters + `send_main_menu()`, `send_list_view()` helpers
- `handlers.py` — thin: call queries + keyboards/views, never build markup inline
