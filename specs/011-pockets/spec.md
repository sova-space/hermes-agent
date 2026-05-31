# Spec 011 — Pockets

## Problem

Category budgets exist (`category_budgets`) but are not dynamically linked to transactions.
There is no visual "envelope" per spending category that drains in real-time as money is spent.

## Solution

Add a **Pockets** system: each pocket maps to one spending category, holds a `balance` (current
remaining spend), and has a `monthly_budget` (the refill amount). Pockets are drained
automatically when Monobank sync saves an expense transaction. On the 1st of each month the
balance resets to `monthly_budget`.

## Tables

- `pockets` — one per category: id, category (unique), monthly_budget, currency, balance, emoji, created_at
- `pocket_transfers` — manual balance movements between pockets: id, from_pocket_id, to_pocket_id, amount, currency, note, created_at

## Routes

| Method | Path | Description |
|---|---|---|
| GET | /pockets | List all pockets |
| POST | /pockets | Create pocket; 409 on duplicate category |
| GET | /pockets/suggest | Categories with >3 months history but no pocket |
| GET | /pockets/{id} | Single pocket |
| PATCH | /pockets/{id} | Update budget/emoji |
| DELETE | /pockets/{id} | Delete |
| POST | /pockets/transfer | Transfer between pockets |
| GET | /pockets/{id}/transactions | Transactions for this pocket's category |

All routes require `verify_webapp_user`.

## Auto-drain

In `sync/monobank.py`, after each new transaction with `amount < 0` and non-null `category`,
call `drain_pocket(session, category, abs(amount), currency)`. Wrapped in try/except so sync
never fails due to a missing pocket.

## Monthly reset

APScheduler job `pocket_monthly_reset` runs `CronTrigger(day=1, hour=0, minute=5)`.
Calls `reset_all_pockets(session)` which sets `balance = monthly_budget` for every pocket.

## Tests

1. Create pocket → appears in list_pockets
2. drain_pocket reduces balance and floors at 0
3. drain_pocket with no matching pocket does not raise
4. reset_all_pockets resets balance back to monthly_budget
