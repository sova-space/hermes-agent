# Spec 007: Finance budgets + Hermes command skill

## Goal

Add per-category monthly budget limits to hermes-finance and teach Hermes to handle
finance slash commands (`/balance`, `/stats`, `/budget`) in the Telegram `#finance` topic.

## Scope

### hermes-finance (data layer)

**New DB table: `category_budgets`**
- `id` UUID PK
- `category` TEXT UNIQUE — matches category strings in `transactions.category`
- `monthly_limit` NUMERIC — positive, in UAH (primary currency)
- `currency` TEXT DEFAULT 'UAH'
- `created_at`, `updated_at` TIMESTAMP

**New REST endpoints (`/budgets`)**
- `GET /budgets` — list all limits `[{category, monthly_limit, currency, spent, remaining, exceeded}]`
  - `spent` is calculated from `transactions/spending` for `this_month`
- `POST /budgets` — upsert a limit `{category, monthly_limit}`
- `DELETE /budgets/{category}` — remove a limit

**New endpoint: `GET /transactions/spending/vs_budget`**
- Returns per-category: `{category, spent, limit, remaining, exceeded: bool}`
- Only categories that have a limit set
- Always scoped to `this_month`

### hermes-agent (skill layer)

**Enhanced `hermes/skills/finance/SKILL.md`**
- `/balance` — GET /accounts, format as emoji table
- `/stats [period]` — GET /transactions/spending, format with category emojis
- `/budget` — GET /budgets, show limits + remaining
- `/budget set <category> <amount>` — POST /budgets
- `/sync` — POST /sync, then GET /sync/status
- Category → emoji mapping table
- All replies go to `#finance` topic (reply in-thread)

## Deferred to phase 2 (needs TELEGRAM_BOT_TOKEN in Railway)
- Proactive budget-exceeded alerts sent directly from hermes-finance after each sync
- `#finance` topic creation (thread ID still FILL_IN)
- `telegram-text` formatting in hermes-finance

## Research reference
- https://cointry.io — review for proactive alert UX and budget category UI
- https://moneko.io — review for spending breakdown and notification design

## Acceptance criteria
- `GET /budgets` returns current month spending vs limits
- `POST /budgets {category: "Groceries", monthly_limit: 5000}` persists a limit
- Hermes responds to `/balance` in `#finance` topic with formatted balances
- Hermes responds to `/stats` with category breakdown + emojis
- Hermes responds to `/budget` with limits + remaining
