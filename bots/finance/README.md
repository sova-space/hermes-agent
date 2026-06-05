# Sova Finance

← [Back to root README](../../README.md)

`@sova_finance_bot` — Monobank integration, budget tracking, and spending analytics. Deployed as a separate Railway service from `sova-claw/hermes-agent`. Exposes a Telegram bot and a REST API that the Hermes orchestrator calls to answer conversational finance questions.

---

## Live features

### Bot commands (`@sova_finance_bot`)

| Command | What it does |
|---|---|
| `/balance` | Current balance for every synced Monobank account |
| `/stats [period] [mode]` | Spending by category. Period: `this_month` `last_month` `last_7d` `last_30d` `last_90d`. Mode: `solo` `couple`. Default: `this_month`. |
| `/budget` | Monthly budget limits vs current spending |
| `/budget set <category> <amount>` | Set a monthly limit for a category |
| `/budget delete <category>` | Remove a limit |
| `/sync` | Trigger Monobank sync immediately |

Periods labeled `this_month` and `last_month` are salary-anchored: the month start shifts to the date the first FOP income arrived, not calendar day 1.

### REST API

Base URL (Railway): `https://finance-api-production-4d72.up.railway.app`

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Service health + last sync status |
| GET | `/accounts` | All account balances |
| PATCH | `/accounts/{id}` | Toggle `is_fop` flag |
| GET | `/transactions` | Recent transactions (`limit`, `period`, `account_id`) |
| GET | `/transactions/spending` | Spending by category (`period`, `account_id`, `exclude_uncategorized`) |
| GET | `/transactions/trend` | Month-by-month income vs expense (`months`, `account_id`) |
| GET | `/transactions/categories` | Canonical category list |
| POST | `/sync` | Trigger sync in background, returns immediately |
| GET | `/sync/status` | Status of last sync run |
| GET | `/budgets` | All budget limits with current-month spending |
| POST | `/budgets` | Create or update a budget limit |
| DELETE | `/budgets/{category}` | Remove a budget limit |

### Scheduler jobs (APScheduler)

| Job | Schedule | What it does |
|---|---|---|
| `monobank_sync` | Every N hours (configurable, default 1) | Full Monobank sync — pulls transactions for all accounts, deduplicates, stores in PostgreSQL |

### Hermes skill

`hermes/skills/finance/SKILL.md` — routes conversational finance questions in the `#finance` Telegram topic to this REST API. Examples: "how much did I spend on food this month?", "am I over budget?", "when was the last sync?". Slash commands go to the bot directly; the skill does not intercept them.

### Spending modes

Transactions are tagged at sync time:
- `solo` — personal spend (MCC-matched expenses)
- `couple` — transfers matching partner's name pattern (configurable via `PARTNER_NAME_PATTERN`)
- `null` — income, cashback

The `mode` filter is available on `/stats`, `GET /transactions`, and `GET /transactions/spending`.

### MCC categorisation

16 canonical categories derived from Monobank MCC codes at sync time:
`Food & Drink`, `Groceries`, `Transportation`, `Healthcare`, `Shopping`, `Entertainment`, `Travel`, `Subscriptions`, `Utilities`, `ATM & Cash`, `Finance`, `Education`, `Pets`, `Cashback`, `Income`, `Couple Transfer`.

---

## Known bugs (fix before new features)

| Bug | Location | Severity |
|---|---|---|
| Multi-currency totals summed without conversion — UAH + USD + EUR added numerically | `insights/queries.py` | High |
| `/sync` bot command calls `run_sync()` synchronously, blocks event loop | `bot/handlers.py` line 100 | High |
| `is_fop` flag overwritten on every sync — manual overrides lost on next hourly run | `sync/monobank.py` `_get_or_create_account` | Medium |
| Category emoji map uses old string literals that no longer match canonical category names — most categories show the fallback box emoji | `bot/formatter.py` + `hermes/skills/finance/SKILL.md` | Medium |

---

## Planned roadmap

### Phase 1 — Bug fixes (block all other work)

Fix the four bugs above in order of severity.

### Phase 2 — Bot redesign

Trim bot commands to three: `/start` (opens Mini App), `/balance`, `/sync`. Remove `/stats` and `/budget` — the Mini App replaces them.

Add proactive notifications (no command needed):
- Daily spending digest at 09:00
- Debt due soon alert
- Weekly goal progress
- Pocket running low / overspent warning
- Trip overspend alert
- Forecast reminder on the 25th of the month

### Phase 3 — New domains

Each domain gets its own DB table(s) and REST routes.

**Debt** — track money owed to/from people.
`GET /debts`, `POST /debts`, `PATCH /debts/{id}`, `DELETE /debts/{id}`

**Goals** — save X by a deadline.
`GET /goals`, `POST /goals`, `DELETE /goals/{id}`

**Trips** — per-trip budget with automatic transaction tagging by date range.
`GET /trips`, `POST /trips`, `GET /trips/{id}/spending`, `DELETE /trips/{id}`

**Buy List** — simple checklist with optional target prices.
`GET /buy-list`, `POST /buy-list`, `PATCH /buy-list/{id}`, `DELETE /buy-list/{id}`

**Forecast** — estimated end-of-month balance.
Formula: `current_balance - remaining_recurring - projected_variable_spend + expected_income`
`GET /forecast`, plus CRUD for recurring items (`/recurring`) and expected income (`/income`).

### Phase 4 — Pockets system

Visual budget containers per spending category. Transactions auto-drain the matching pocket at sync time.

New tables: `pockets`, `pocket_transfers`.
`GET /pockets`, `POST /pockets`, `PATCH /pockets/{id}`, `DELETE /pockets/{id}`, `PATCH /pockets/transfer`, `GET /pockets/suggest`, `GET /pockets/{id}/transactions`

### Phase 5 — Couple mode

Two Monobank users, shared and personal pockets. Invite flow via Telegram.

New table: `users` (with `telegram_user_id`, `mono_token`, `role`).
Ownership column on pockets/goals/trips: `"personal:<user_id>"` or `"shared"`.
`GET /settings/mode`, `POST /settings/couple/invite`, `POST /settings/couple/join`, `DELETE /settings/couple`

### Phase 6 — Bank abstraction

Define a `BankClient` interface. Refactor `MonobankClient` to implement it. No new banks added yet — establishes the extension point.

### Phase 7 — Mini App

Single-page Telegram Mini App served at `/miniapp`. Plain HTML + CSS + vanilla JS, mobile-first. Screens: Home, Pockets, Debt, Goals, Trips, Buy List, Forecast, Settings. Replaces `/stats` and `/budget` bot commands as the primary UI.

### Phase 8 — Additional scheduler jobs

Jobs to add alongside `monobank_sync`:

| Job | Trigger | Purpose |
|---|---|---|
| `daily_digest` | 09:00 daily | Push spending summary to Telegram |
| `debt_check` | Daily | Alert on debts due within 3 days |
| `goal_update` | Weekly | Push goal progress |
| `trip_check` | Daily | Alert when active trip is near budget limit |
| `pocket_check` | Daily | Alert on pockets running low or over |
| `pocket_monthly_reset` | 1st of month | Reset pocket spending counters |
| `forecast_reminder` | 25th of month | Push month-end forecast |

---

## Not yet built

- Telegram Mini App (Phase 7)
- Debt, Goals, Trips, Buy List, Forecast domains (Phase 3)
- Pockets system (Phase 4)
- Couple mode (Phase 5)
- Bank abstraction layer (Phase 6)
- All proactive notifications (Phase 2)

---

## Troubleshooting

**Sync not running / last sync is stale**
1. Check Railway logs: `railway logs` or service → Deployments → Logs
2. Verify `MONOBANK_TOKEN` is valid: `curl -H "X-Token: $TOKEN" https://api.monobank.ua/personal/client-info`
3. Check `GET /sync/status` — if `last_error` is set, the token is likely expired or rate-limited (Monobank rate-limits to 1 request/minute per token)

**Bot not responding**
1. Confirm `TELEGRAM_OWNER_ID` matches your Telegram user ID (handlers reject all other users)
2. Check `TELEGRAM_BOT_TOKEN` is still valid via `@BotFather`
3. Look for `telegram_bot_started` in logs — if absent, the bot failed to start

**Migration failed on deploy**
1. Check Railway pre-deploy logs for the `alembic upgrade head` step
2. Connect to DB: `railway connect postgres` then inspect `alembic_version` table
3. If head is ahead of DB, the migration has a syntax error — check `alembic/versions/`

**`/stats` shows 📦 for every category**
Known bug: emoji map uses stale string literals. Tracked in [known bugs](#known-bugs-fix-before-new-features).

**Adding a new bot command**
1. Add handler in `finance_api/domains/bot/handlers.py` (owner-gate with `TELEGRAM_OWNER_ID` check)
2. Register command in `finance_api/domains/bot/runner.py`
3. Keep handlers thin — call into `domains/` for any logic

**Adding a new REST endpoint**
1. Add router function in `finance_api/routers/`
2. Add query/logic in the relevant `finance_api/domains/` subdomain
3. Register the router in `finance_api/main.py`
4. Add a migration if schema changes: `uv run alembic revision --autogenerate -m "description"`

---

## Stack

| Concern | Choice |
|---|---|
| Web framework | FastAPI + Pydantic v2 |
| ORM | SQLModel + Alembic |
| DB driver | psycopg 3 |
| Telegram bot | aiogram 3.x |
| Scheduler | APScheduler |
| Logging | structlog (JSON in prod) |
| Deploy | Railway, multi-stage Dockerfile |

---

## Local dev

```bash
# Build from repo root
docker build -f bots/finance/Dockerfile bots/finance/

# Or with all services (shared db)
docker compose -f infra/docker-compose.yml up finance db
```

Copy `infra/.env.finance.local.example` to `infra/.env.finance.local` and fill in secrets.

```bash
# Tests (from bots/finance/)
uv run pytest tests/

# Lint
uv run ruff check finance_api/
```

---

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | `postgresql+psycopg://...@host:5432/finance` |
| `TELEGRAM_BOT_TOKEN` | yes | From @BotFather |
| `TELEGRAM_OWNER_ID` | yes | Telegram user ID — owner gate on all handlers |
| `MONOBANK_TOKEN` | yes | Personal token from Monobank |
| `FINANCE_API_KEY` | yes | Shared secret for Hermes skill auth |
| `FOP_ACCOUNT_IDS` | no | Comma-separated Monobank account IDs to flag as FOP/salary |
| `PARTNER_NAME_PATTERN` | no | Regex to match partner name in transfer descriptions |
| `SYNC_INTERVAL_HOURS` | no | Sync frequency (default: 1) |
| `MONOBANK_FETCH_DAYS` | no | How far back initial sync reaches (default: 90) |
| `MINI_APP_URL` | no | Public URL of the Mini App — set to `https://finance-api-production-4d72.up.railway.app/miniapp` |

---

## Railway deployment

- Project: `finance-agent` (`186cf9f1-f88f-4b73-b286-a055e107cc9d`)
- Service: `finance-api` (`b6cb492f-9100-4330-82db-8afd95d6fe91`)
- Root directory: `bots/finance/`
- Pre-deploy: `alembic upgrade head` via `entrypoint.sh`
- Database: `finance` DB on shared `hermes-db` PostgreSQL

Railway does **not** auto-deploy on git push. Always run:

```bash
cd bots/finance
railway link --project 186cf9f1-f88f-4b73-b286-a055e107cc9d --service b6cb492f-9100-4330-82db-8afd95d6fe91
railway up --detach
```
