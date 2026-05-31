# Spec 010 — Phase 3: New Domains

**Status:** Draft — awaiting architect feasibility review before dev starts.

---

## 1. Problem

The Mini App (Phase 7) and proactive notifications (Phase 2) both depend on five new data
domains that don't exist yet: Debt, Goals, Trips, Buy List, and Forecast. Without them the
bot is read-only Monobank analytics. Users can't track money owed to friends, savings goals,
trip budgets, or a wishlist — all things Nazar actively needs.

Additionally, before any Mini-App-facing route is built, there must be a FastAPI dependency
that validates a Telegram WebApp initData HMAC and identifies the caller. Every Phase 3–7
router that the Mini App calls will use it.

---

## 2. Solution

### 2.1 — initData auth dependency

A single FastAPI dependency `verify_webapp_user(request: Request) -> int` placed in
`finance_api/core/auth/webapp.py` (proposed path — architect to confirm). It:

1. Reads the `Authorization: tma <initData>` header from the incoming HTTP request.
   The `tma` prefix is the Telegram Mini App convention.
2. URL-decodes the initData string and parses it as query parameters.
3. Validates the HMAC per the Telegram WebApp documentation:
   - `secret_key = HMAC-SHA256(key=b"WebAppData", message=bot_token.encode())`
   - `data_check_string` = newline-joined `key=value` pairs, sorted alphabetically,
     excluding the `hash` key
   - Expected hash = `HMAC-SHA256(key=secret_key, message=data_check_string.encode()).hexdigest()`
   - Dev must implement against the Telegram docs, not from memory:
     https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
4. Checks `auth_date` freshness — rejects initData older than 24 hours.
5. Parses `user.id` from the `user` JSON field of initData.
6. Compares that ID against `settings.telegram_owner_id` — non-owner requests raise
   HTTP 403. Hermes is single-user; no multi-user path is opened here.
7. Returns `telegram_user_id: int`.

**Fail-closed rules (non-negotiable):**
- If `settings.telegram_bot_token` is `None`, the dependency raises HTTP 503 with body
  `{"detail": "Bot token not configured"}` — never passes auth.
- Tampered hash → HTTP 401.
- Missing or expired `auth_date` → HTTP 401.
- Non-owner user ID → HTTP 403.
- Any parse error → HTTP 401.

`settings.telegram_owner_id` must be added to `Settings` as `int` — required, no default.
This matches the existing `TELEGRAM_OWNER_ID` env var already used by the bot.

**Auth scope coexistence:**
Phase 3 routes are Mini-App-facing. The existing `/budgets`, `/transactions`, etc. routes
are Hermes-skill-facing (no auth today — an open question for the architect about whether
API-key auth should be retrofitted). Phase 3 routes use initData auth only. The two
audiences must not be conflated.

---

### 2.2 — Debt domain

Track money Nazar lent to or borrowed from people.

**DB table: `debts`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | `default_factory=uuid4` |
| `person` | text, not null | Free-text name, e.g. "Олена" |
| `amount` | float, not null | Positive = owed to Nazar; negative = Nazar owes |
| `currency` | text, not null, default `"UAH"` | ISO 4217 |
| `description` | text, nullable | Context note |
| `due_date` | date, nullable | Optional repayment deadline |
| `settled_at` | datetime, nullable | Set when resolved; null = still open |
| `created_at` | datetime, not null | UTC, `default_factory` |

**API routes (all require initData auth):**

| Method | Path | Description |
|---|---|---|
| GET | `/debts` | List all debts. Query param: `settled=false` (default) / `true` / `all` |
| POST | `/debts` | Create a new debt record |
| PATCH | `/debts/{id}` | Update `person`, `amount`, `description`, `due_date`, or `settled_at` |
| DELETE | `/debts/{id}` | Delete a debt record. Returns 404 if not found |

POST body fields: `person`, `amount`, `currency` (default UAH), `description` (optional),
`due_date` (optional).

PATCH body: all fields optional; sending `settled_at=<iso_datetime>` marks as settled.
Convenience: sending `settled=true` in PATCH sets `settled_at` to `now()` without requiring
the caller to know the timestamp.

---

### 2.3 — Goals domain

Save a target amount by a deadline, linked to a specific Monobank account balance.

**DB table: `goals`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | text, not null | e.g. "MacBook fund" |
| `target_amount` | float, not null | Target to reach |
| `currency` | text, not null, default `"UAH"` | |
| `account_id` | UUID FK → `accounts.id`, nullable | Source account for progress tracking. Nullable because account may not be synced yet. |
| `deadline` | date, nullable | Optional target date |
| `notes` | text, nullable | |
| `created_at` | datetime, not null | UTC |
| `achieved_at` | datetime, nullable | Set when balance reached target |

**Open question for architect:** Goals progress is computed by comparing the linked
account's current balance against `target_amount`. Is `account_id` the right FK strategy,
or should we track a manually-updated `current_amount`? The account-balance approach is
automatic but means a goal is always "at 100% of current balance," which doesn't make sense
for accounts with multiple goals. Architect to decide before dev implements
`GET /goals` progress calculation.

**API routes (all require initData auth):**

| Method | Path | Description |
|---|---|---|
| GET | `/goals` | List goals with computed progress (if account linked) |
| POST | `/goals` | Create a goal |
| PATCH | `/goals/{id}` | Update name, target, deadline, account_id, notes, achieved_at |
| DELETE | `/goals/{id}` | Delete a goal |

---

### 2.4 — Trips domain

Per-trip spending budget. Transactions that fall within a trip's date range are automatically
included in the trip's spending total at query time (no write-time tagging needed).

**DB table: `trips`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | text, not null | e.g. "Barcelona May 2026" |
| `budget` | float, nullable | Total budget for the trip |
| `currency` | text, not null, default `"UAH"` | |
| `start_date` | date, not null | Inclusive |
| `end_date` | date, not null | Inclusive |
| `notes` | text, nullable | |
| `created_at` | datetime, not null | UTC |

**Constraint:** `end_date >= start_date` enforced at the application layer (Pydantic
validator on POST/PATCH body). Architect to advise whether a DB CHECK constraint should
also be added.

**API routes (all require initData auth):**

| Method | Path | Description |
|---|---|---|
| GET | `/trips` | List all trips |
| POST | `/trips` | Create a trip |
| GET | `/trips/{id}/spending` | Return spending breakdown for trip's date range |
| PATCH | `/trips/{id}` | Update name, budget, dates, notes |
| DELETE | `/trips/{id}` | Delete a trip |

`GET /trips/{id}/spending` calls the existing spending-by-category query scoped to
`[trip.start_date, trip.end_date]`. It **must** use the corrected multi-currency aggregation
introduced in the Phase 1 bug fixes — do not sum across currencies.

---

### 2.5 — Buy List domain

A simple wishlist with optional target prices.

**DB table: `buy_list_items`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | text, not null | e.g. "AirPods Pro" |
| `target_price` | float, nullable | Approximate cost |
| `currency` | text, nullable | ISO 4217; required if `target_price` is set |
| `url` | text, nullable | Optional product link |
| `notes` | text, nullable | |
| `bought_at` | datetime, nullable | Set when purchased |
| `created_at` | datetime, not null | UTC |

**API routes (all require initData auth):**

| Method | Path | Description |
|---|---|---|
| GET | `/buy-list` | List all items. Query param: `bought=false` (default) / `true` / `all` |
| POST | `/buy-list` | Create an item |
| PATCH | `/buy-list/{id}` | Update any field; send `bought=true` to mark as purchased |
| DELETE | `/buy-list/{id}` | Delete an item |

PATCH convenience: `bought=true` sets `bought_at` to `now()` (same pattern as Debt settle).

---

### 2.6 — Forecast domain

Estimate end-of-month balance from current balance, expected income, known recurring
expenses, and projected variable spend.

Formula: `forecast = current_balance - remaining_recurring - projected_variable_spend + expected_income`

**DB table: `recurring_items`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | text, not null | e.g. "Netflix" |
| `amount` | float, not null | Monthly cost; positive |
| `currency` | text, not null, default `"UAH"` | |
| `day_of_month` | int, nullable | Day payment usually hits (1–31) |
| `category` | text, nullable | Canonical category, for matching against transactions |
| `active` | bool, not null, default `True` | Inactive items excluded from forecast |
| `created_at` | datetime, not null | UTC |

**DB table: `expected_income_items`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | text, not null | e.g. "Salary" |
| `amount` | float, not null | Expected amount; positive |
| `currency` | text, not null, default `"UAH"` | |
| `day_of_month` | int, nullable | Expected arrival day |
| `active` | bool, not null, default `True` | |
| `created_at` | datetime, not null | UTC |

**Open question for architect:** `projected_variable_spend` — two candidate approaches:
1. Run-rate: `(days_elapsed / days_in_month) * current_month_spending`, scaled to month-end.
2. Historical average: average spending of same category from last N months.

The run-rate is simpler and requires no additional data. Historical average is more accurate
but needs a configurable N and currency-safe aggregation. Architect to decide before dev
implements the `GET /forecast` computation.

**Open question for architect:** Multi-account forecast — should `current_balance` be the
sum of all accounts or only the primary FOP account? The FOP account is what salary lands on.
Might be simplest to sum all non-FOP accounts as "spending accounts" + FOP separately.

**API routes (all require initData auth):**

| Method | Path | Description |
|---|---|---|
| GET | `/forecast` | Computed forecast for current month |
| GET | `/recurring` | List recurring items |
| POST | `/recurring` | Create a recurring item |
| PATCH | `/recurring/{id}` | Update or deactivate |
| DELETE | `/recurring/{id}` | Delete |
| GET | `/income` | List expected income items |
| POST | `/income` | Create an expected income item |
| PATCH | `/income/{id}` | Update or deactivate |
| DELETE | `/income/{id}` | Delete |

---

## 3. Scope

### In scope

- `verify_webapp_user` FastAPI dependency in `finance_api/core/auth/`
- Five new domain model files (SQLModel, `table=True`)
- Five new router files under `finance_api/routers/`
- Five new query modules under `finance_api/domains/<domain>/queries.py`
- Migration `0008` — all new tables in one migration
- Router registration in `composition.py`
- `telegram_owner_id` added to `Settings`
- Tests: minimum 3 per domain + auth dependency tests (see section 5)

### Out of scope

- Ownership columns / multi-user (Phase 5 Couple mode)
- Pocket auto-drain from Trips (Phase 4)
- Notifications/scheduler jobs for new domains (Phase 8)
- Retrofit API-key auth onto existing routers — existing routes stay unprotected as today
- Mini App frontend (Phase 7)
- Any change to Phase 1 bug fixes already landed

---

## 4. User flows

### Debt flow

1. User creates a debt: POST `/debts` `{person: "Іванко", amount: 500, currency: "UAH", description: "lunch"}`
2. User lists open debts: GET `/debts` — sees Іванко owes 500 UAH
3. Debt is repaid: PATCH `/debts/{id}` `{settled: true}`
4. GET `/debts` (default `settled=false`) — Іванко no longer in list

### Goal flow

1. User creates a goal: POST `/goals` `{name: "MacBook", target_amount: 90000, currency: "UAH", account_id: "<uuid>"}`
2. User checks progress: GET `/goals` — sees current account balance vs 90,000 UAH target

### Trip flow

1. User creates trip: POST `/trips` `{name: "Warsaw", budget: 15000, currency: "UAH", start_date: "2026-06-01", end_date: "2026-06-07"}`
2. Transactions sync normally (no change to sync code)
3. During trip: GET `/trips/{id}/spending` — spending breakdown by category for Jun 1–7

### Buy List flow

1. User adds item: POST `/buy-list` `{name: "AirPods Pro", target_price: 9000, currency: "UAH"}`
2. Buys it: PATCH `/buy-list/{id}` `{bought: true}`
3. GET `/buy-list` — item gone (default `bought=false` filter)

### Forecast flow

1. User adds recurring: POST `/recurring` `{name: "Netflix", amount: 199, currency: "UAH", day_of_month: 15}`
2. User adds income: POST `/income` `{name: "Salary", amount: 120000, currency: "UAH", day_of_month: 5}`
3. GET `/forecast` — returns estimated balance at month-end

---

## 5. Success criteria

### Auth dependency

- Valid Telegram initData → returns `telegram_user_id`
- Tampered `hash` → HTTP 401
- `auth_date` older than 24 hours → HTTP 401
- Non-owner user ID → HTTP 403
- `telegram_bot_token = None` → HTTP 503
- Missing `Authorization` header → HTTP 401

### Per-domain (minimum 3 tests each)

**Debt:**
- Create debt → retrieved by GET `/debts`
- Settled debt absent from default (open) list, present in `settled=true`
- DELETE non-existent ID → 404

**Goals:**
- Create goal → appears in GET `/goals`
- DELETE goal → 404 on repeat request
- Goal with null `account_id` has no progress computation (no crash)

**Trips:**
- Create trip with `end_date < start_date` → HTTP 422
- GET `/trips/{id}/spending` returns spending scoped to trip date range
- GET `/trips/{id}/spending` on non-existent trip → 404

**Buy List:**
- Create item → appears in GET `/buy-list` (default: unbought)
- Mark bought → absent from default list, present in `bought=true`
- PATCH non-existent ID → 404

**Forecast:**
- GET `/forecast` with no recurring/income → returns zero projections without error
- Create recurring item → appears in GET `/recurring`
- Deactivate recurring item (`active=false`) → excluded from `/forecast` calculation

### Migration

- Migration 0008 applies cleanly on a fresh DB (`alembic upgrade head`)
- `alembic downgrade 0007` removes all new tables cleanly

---

## 6. Open questions

These must be resolved by architect before dev starts on the affected domain:

| # | Question | Affects |
|---|---|---|
| OQ1 | Where exactly does `verify_webapp_user` live? Proposed: `finance_api/core/auth/webapp.py`. Is `core/auth/` the right sub-package, or should it be a standalone `finance_api/dependencies.py`? | All Phase 3–7 routes |
| OQ2 | Goals progress strategy: FK to `accounts.id` (automatic, from account balance) vs. manually-updated `current_amount` column? | Goals model + `GET /goals` |
| OQ3 | Forecast `projected_variable_spend`: run-rate (simpler) vs. historical N-month average (more accurate)? | Forecast computation |
| OQ4 | Forecast multi-account: sum all accounts, or separate FOP vs. spending accounts? | `GET /forecast` |
| OQ5 | Should a DB CHECK constraint enforce `trips.end_date >= trips.start_date`, or is app-level Pydantic validation sufficient? | Migration 0008 + `trips` table |
| OQ6 | Auth for existing routes: should API-key auth be retrofitted onto `/budgets`, `/transactions`, etc. in this spec or deferred? Current state: unprotected. | Existing routers |

---

## 7. Technical notes for dev

These are constraints, not design decisions (architect sign-off still required on OQ1–OQ6):

- **Model imports in conftest:** The test conftest builds SQLite schema via
  `SQLModel.metadata.create_all`. Every new model must be imported somewhere that executes
  before `create_all` runs, or tests will operate on missing tables. Follow the pattern in
  `tests/conftest.py` — import each new model class explicitly at the top.

- **Currency per record:** Every money-bearing column (`amount`, `budget`, `target_amount`,
  `target_price`, `monthly_cost`) must have a sibling `currency` column. Phase 1 fixed
  naive cross-currency summation; do not reintroduce it.

- **Trips spending query:** `GET /trips/{id}/spending` must pass `start_date`/`end_date` to
  the existing `get_spending_by_category` query (or its equivalent), not write a new query
  that sums amounts naively.

- **Migration 0008:** Hand-written like 0007. `down_revision = "0007"`. All CREATE TABLEs
  in one `upgrade()`. Real `downgrade()` that drops all new tables in reverse dependency
  order. No backfill needed — all tables are new.

- **Router prefixes to register in `composition.py`:**

  | Router module | Prefix | Tag |
  |---|---|---|
  | `routers/debts.py` | `/debts` | `debts` |
  | `routers/goals.py` | `/goals` | `goals` |
  | `routers/trips.py` | `/trips` | `trips` |
  | `routers/buy_list.py` | `/buy-list` | `buy-list` |
  | `routers/forecast.py` | `/forecast` | `forecast` |
  | `routers/recurring.py` | `/recurring` | `recurring` |
  | `routers/income.py` | `/income` | `income` |

- **TELEGRAM_OWNER_ID in Settings:** Add `telegram_owner_id: int` to `Settings` in
  `finance_api/core/config.py`. This is a required field (no default). The bot already
  expects `TELEGRAM_OWNER_ID` in the environment; this makes it accessible to the auth
  dependency.

- **Dependency signature:** `verify_webapp_user` must be a callable FastAPI dependency
  usable as `Depends(verify_webapp_user)` at the router level, not per-route.
  Example router opening:
  ```python
  router = APIRouter(dependencies=[Depends(verify_webapp_user)])
  ```
