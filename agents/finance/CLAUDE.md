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

## Railway

Service: `hermes-finance` in `sova-claw` workspace.
Root directory: `agents/finance` (set in Railway service settings).
Deploy: push to `main` branch of `sova-claw/hermes-agent` → Railway auto-deploys.
Pre-deploy: `alembic upgrade head` runs automatically via `entrypoint.sh`.

Database: `finance` database on shared `hermes-db` PostgreSQL service.

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
