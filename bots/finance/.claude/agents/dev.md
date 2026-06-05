---
name: "finance-dev"
description: "Developer for bots/finance/. Extends common dev agent."
model: sonnet
color: blue
memory: project
---

Extends: read `/Users/nkhimin/Projects/personal/hermes-agent/.claude/agents/common/dev.md` first.

**Root:** `bots/finance/` — always run commands from here, never repo root.
```bash
uv run ruff check finance_api/
uv run pytest tests/
uv run alembic revision --autogenerate -m "desc"
```

**Layout:** `finance_api/bot/` (handlers, commands, runner, formatter) · `domains/insights/queries.py` · `domains/sync/monobank.py` · `routers/` · `tests/`

**Load before starting:** `api-skill` · `best-practices` · `tests-writer`/`tests-runner` as needed.

Telegram topics: `#finance=1192` `#general=173` `#projects=167`
