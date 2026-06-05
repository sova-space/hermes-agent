---
name: "wishlist-dev"
description: "Developer for bots/wishlist/. Extends common dev agent."
model: sonnet
color: blue
---

Extends: read `/Users/nkhimin/Projects/personal/hermes-agent/.claude/agents/dev.md` first.

**Root:** `bots/wishlist/` · `wishlist_api/`
```bash
uv run ruff check wishlist_api/
uv run alembic revision --autogenerate -m "desc"
```

**Layout:** `domains/wish/models.py` (WishUser, Wishlist, WishItem) · `domains/wish/queries.py` · `domains/bot/` (commands, runner, handlers, keyboards, views) · `routers/health.py` · `routers/miniapp.py`

**Callback scheme:** `menu` · `open:<id>` · `newlist` · `additem:<id>` · `share:<id>` · `dellist:<id>` · `remove:<id>` · `claim:<id>` · `unclaim:<id>`

**States:** `AWAITING_LIST_NAME` · `AWAITING_ITEM`

**Env:** `DATABASE_URL` · `TELEGRAM_BOT_TOKEN` · `BOT_USERNAME` · `OPENROUTER_API_KEY`
