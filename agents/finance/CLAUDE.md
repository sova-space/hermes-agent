# agents/finance — Finance Sub-Agent

`@sova_finance_bot` — Monobank integration, budget tracking, spending analytics. Deployed as a separate Railway service from `sova-claw/hermes-agent` (this repo).

```
finance_api/   — FastAPI + aiogram + APScheduler (single Railway service)
  bot/           — aiogram bot, handlers, commands
  domains/
    insights/      — queries.py (analytics)
    sync/          — Monobank sync (APScheduler, hourly)
    accounts/      — Account model
    transactions/  — Transaction model
  routers/       — REST API endpoints (called by hermes finance skill)
tests/         — pytest unit tests
```

## Core Architecture Rules

```
bot/handlers.py  →  domains/insights/queries.py (analytics)
domains/sync/monobank.py  →  DB directly (APScheduler, hourly)
routers/         →  called by hermes finance skill via HTTP
```

- Handlers are Telegram boundary only — no analytics logic.
- Queries take `Session`, return plain dicts/lists — no HTTP, no AI.
- All config from `Settings`. No hardcoded tokens, URLs, or intervals.

## Bot command sync pattern

`bot/commands.py` is the single source of truth for all bot commands:

- `BOT_COMMANDS` — list of `BotCommand` objects
- `setup_bot(bot)` — called once on startup; registers commands + menu button
- `GET /bot/commands` — endpoint Hermes reads to know which commands this bot owns

**To add a command**: add it to `BOT_COMMANDS` and wire a handler in `runner.py`. Nothing else needed — Hermes stays in sync via the API.

## Railway

Service: `hermes-finance` in `hermes-main` project (`3d73dc58-1201-4258-bc1d-1f9c24333032`).
Service ID: `9bc27c48-c35d-4dcf-9f4e-ba3c73e1ed96`
Root directory: `agents/finance` (set in Railway service settings).
Dockerfile: `agents/finance/Dockerfile` (full path from repo root).
Deploy: push to `main` branch → Railway auto-deploys (watch pattern: `agents/finance/**`).
Pre-deploy: `alembic upgrade head` runs automatically via `entrypoint.sh`.
Public URL: `https://hermes-finance-production.up.railway.app`

Database: `Postgres` service in `hermes-main` project (ID: `b6daf7a2-de33-4767-a78b-e4e4d7424d58`).
Internal URL: `postgres.railway.internal:5432`

## Building locally

```bash
# From repo root:
docker build -f agents/finance/Dockerfile agents/finance/

# With docker compose (all services + shared db):
docker compose -f infra/docker-compose.yml up finance db
```

Copy `infra/.env.finance.local.example` → `infra/.env.finance.local` and fill in secrets.

## Guardrails

- Never push directly to `main` — use a branch.
- Never hardcode secrets, tokens, or API keys in source.
- Required config fails loud if missing (no silent defaults in `Settings`).
- Owner-gate every Telegram handler via `TELEGRAM_OWNER_ID`.

## Commit Style

```
<scope>: <what>  (imperative, lowercase)

feat(sync): add cashback transaction handling
fix(bot): handle empty account list in /status
chore(deps): bump aiogram to 3.14.0
```

## Workflow

- `ruff check finance_api/` before committing.
- `/code-review` before merging.
