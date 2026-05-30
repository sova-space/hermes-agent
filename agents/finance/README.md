# hermes-finance

`@sova_finance_bot` — Monobank integration, budget tracking, spending analytics. Deployed as a separate Railway service from `sova-claw/hermes-agent`.

## What it does

- **Bot commands** in the `#finance` Telegram topic: `/balance`, `/spending`, `/sync`, `/budget`
- **REST API** called by the Hermes finance skill to answer conversational money questions
- **Hourly Monobank sync** via APScheduler: pulls transactions, stores in PostgreSQL
- **Budget tracking** per category with monthly limits

## Architecture

```
@sova_finance_bot (Telegram)
        │
   aiogram handlers  (domains/bot/handlers.py)
        │
   insights queries  (domains/insights/queries.py)
        │
   PostgreSQL  ←  Monobank sync (APScheduler, hourly)

Hermes skill  (hermes/skills/finance/SKILL.md)
        │ HTTP
   FastAPI routers  (routers/)
        │
   insights queries  (same layer)
```

## Stack

| Concern       | Choice                          |
|---------------|---------------------------------|
| Web framework | FastAPI + Pydantic v2           |
| ORM           | SQLModel + Alembic              |
| DB driver     | psycopg 3                       |
| Telegram bot  | aiogram 3.x                     |
| Scheduler     | APScheduler                     |
| Logging       | structlog (JSON)                |
| Deploy        | Railway, multi-stage Dockerfile |

## Local dev

```bash
# From repo root
docker build -f agents/finance/Dockerfile agents/finance/

# Or with all services
docker compose -f infra/docker-compose.yml up finance db
```

Copy `infra/.env.finance.local.example` → `infra/.env.finance.local` and fill in secrets.

## Environment variables

| Variable             | Required | Notes                                      |
|----------------------|----------|--------------------------------------------|
| `DATABASE_URL`       | yes      | `postgresql+psycopg://…@host:5432/finance` |
| `TELEGRAM_BOT_TOKEN` | yes      | From @BotFather                            |
| `TELEGRAM_OWNER_ID`  | yes      | Your Telegram user ID (owner gate)         |
| `MONOBANK_TOKEN`     | yes      | Personal token from Monobank               |
| `FINANCE_API_KEY`    | yes      | Shared secret for Hermes skill auth        |

## Railway

- Service: `hermes-finance` in `sova-claw` workspace
- Root directory: `agents/finance/`
- Pre-deploy: `alembic upgrade head` runs via `entrypoint.sh`
- Database: `finance` DB on shared `hermes-db` PostgreSQL service
