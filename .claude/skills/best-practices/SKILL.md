---
name: best-practices
description: Python best practices for bots/finance. Covers FastAPI patterns, Pydantic v2, async rules, SQLModel, structlog, and python-telegram-bot (PTB) conventions. Load during implementation or review.
version: 1.1.0
---

# Python Best Practices — bots/finance

Rules for this repo's stack. Repo conventions always win over generic advice.

---

## Async / sync

This repo is **async** (PTB, APScheduler, FastAPI async routes). Apply this rule:

| What the code does | Use |
|---|---|
| Non-blocking awaitable I/O (httpx, PTB, asyncpg) | `async def` |
| Blocking call (matplotlib, file I/O, sync DB) | run in threadpool or sync route |
| CPU-bound > 50 ms | Offload to a thread, not inline in event loop |

Never call `time.sleep` or blocking I/O inside `async def` — it freezes the event loop and blocks Telegram polling.

Use `asyncio.to_thread()` or `loop.run_in_executor()` for blocking operations inside async context:

```python
import asyncio

# matplotlib is blocking — offload it
chart_path = await asyncio.to_thread(charts.pie_by_category, data)
```

---

## Pydantic v2

Use `X | None` — not `Optional[X]` (PEP 604):

```python
notes: str | None = None
```

Use built-in validators via `Field(min_length=..., ge=...)` over manual `@field_validator` where possible.

Use `@field_serializer` for custom JSON serialization — `json_encoders` is removed in Pydantic v2.

---

## SQLModel + sessions

Always pass `Session` explicitly to query functions. Never access a global session singleton.

Call `session.expire_all()` after a commit if you need to re-read the same objects in the same request.

Use `select(Model).where(...)` — not raw SQL strings.

---

## structlog

```python
import structlog

log = structlog.get_logger(__name__)

log.info("sync_completed", accounts=3, tx_imported=47)
log.error("monobank_fetch_failed", account_id=str(account.id), error=str(exc))
```

- Event names: `snake_case` verbs (`sync_completed`, `tool_dispatched`).
- Context as `key=value` pairs — never format strings.
- Never `print()` or stdlib `logging` directly.

---

## Settings

All config via `core/config.py`:

```python
from finance_api.core.config import get_settings

settings = get_settings()
```

`get_settings()` is cached with `@lru_cache`. Never instantiate `Settings()` directly in application code.

---

## python-telegram-bot (PTB) handlers

The bot uses **python-telegram-bot** (`telegram` package), NOT aiogram.

```python
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application

async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != get_settings().telegram_owner_id:
        return
    ...
    await update.message.reply_text(text, parse_mode="HTML")
```

Register handlers in `runner.py`:
```python
app.add_handler(CommandHandler("balance", cmd_balance))
```

WebApp keyboard button (for Mini App):
```python
from telegram import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup

keyboard = InlineKeyboardMarkup([[
    InlineKeyboardButton("Open Finance", web_app=WebAppInfo(url=settings.mini_app_url))
]])
await update.message.reply_text("Finance", reply_markup=keyboard)
```

Sending from APScheduler threads (sync context → async bot):
```python
# Capture at lifespan startup:
loop = asyncio.get_event_loop()
# In scheduler job (sync thread):
asyncio.run_coroutine_threadsafe(
    application.bot.send_message(chat_id=..., text=..., message_thread_id=...),
    loop
)
```

- Always owner-gate at the top of every handler.
- Use `reply_text(text, parse_mode="HTML")` for formatted text.
- Use `reply_photo(photo=open(path, "rb"))` for charts, then `os.unlink(path)`.
- Keep handlers thin — delegate to query functions; no analytics logic in handlers.

---

## Claude tool use loop

```python
response = client.messages.create(
    model="claude-opus-4-7",
    tools=TOOLS,
    messages=messages,
)
while response.stop_reason == "tool_use":
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            result = dispatch(block.name, block.input, session)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })
    messages = messages + [
        {"role": "assistant", "content": response.content},
        {"role": "user", "content": tool_results},
    ]
    response = client.messages.create(model=..., tools=TOOLS, messages=messages)
```

- Always loop until `stop_reason != "tool_use"`.
- Tool results must be JSON strings — serialize with `json.dumps`.
- Use the latest capable model (`claude-opus-4-7`) for financial reasoning.

---

## Charts

```python
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for server use
import matplotlib.pyplot as plt
```

Always set `Agg` backend before importing `pyplot`. Matplotlib is not thread-safe — always generate charts in a single thread or use `asyncio.to_thread`.

Save to a tmp file and return the path:

```python
import tempfile

with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
    plt.savefig(f.name, bbox_inches="tight")
    return f.name
```

---

## Anti-patterns

| Anti-pattern | Fix |
|---|---|
| `time.sleep` in `async def` | Use `asyncio.sleep` or offload to thread |
| `print()` anywhere | Use `structlog` |
| `Optional[X]` | Use `X \| None` |
| Hardcoded token/URL/interval | Move to `Settings` |
| Analytics logic in bot handlers | Move to query functions; handlers are boundary only |
| Direct DB access in `charts.py` | Pass data in, not session |
| Missing owner gate in handler | Add `telegram_owner_id` check first |
| `matplotlib.pyplot` without `Agg` backend | Set `matplotlib.use("Agg")` at module top |
| Forgetting to clean up chart tmp file | Always `os.unlink(path)` after send |
