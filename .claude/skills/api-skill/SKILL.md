---
name: api-skill
description: MUST invoke before any edit or review inside finance_api/. Layering rules, sync conventions, migration rules.
version: 1.1.0
---

## Layering

```
bot/handlers.py  →  domains/insights/tools.py  →  queries.py / charts.py
domains/sync/monobank.py  →  DB directly
```

- `handlers.py` — Telegram boundary: owner-gate first, call dispatch/queries, send response. No analytics.
- `tools.py` — Claude tool definitions + `dispatch()`. Returns plain dicts/lists.
- `queries.py` — analytics reads. Takes `Session`, returns plain dicts/lists. No HTTP, no Telegram.
- `charts.py` — matplotlib only. Takes plain data, returns tmp PNG path. No DB.
- `monobank.py` — owns idempotency via `monobank_id` unique constraint.

## Monobank sync

- Idempotency: `monobank_id` unique — use `INSERT ... ON CONFLICT DO NOTHING` or catch `IntegrityError`
- Rate limit: 1 API call / 60s per token — respect between account fetches
- `SyncRun`: write `started_at` first, update `completed_at`/`tx_imported`/`status` at end; on error set `status="error"`

## Migrations

- `batch_alter_table` for all `alter_column`/`add_column`
- Real `downgrade()` — never `pass`
- `server_default` on every new NOT NULL column
- `datetime.now(timezone.utc)` — never `datetime.utcnow()`

## Reject in review

Analytics in handlers · DB access in `charts.py` · HTTP in `queries.py` · missing owner-gate · `print()` · hardcoded tokens · `Optional[X]` · unhandled `monobank_id` conflicts · chart tmp not cleaned up
