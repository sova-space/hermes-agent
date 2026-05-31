# Spec 009: Spending modes, better categorization, and salary-anchored periods

## What it does

Three related improvements to the finance sub-agent:

1. **Spending modes** — every transaction is tagged `solo` or `couple`. Queries accept an optional `mode` filter so Nazar can see personal vs. shared spending separately.
2. **Better categorization** — add `Couple Transfer` and `Income` canonical categories; auto-tag transfers to Olena as `couple` mode; auto-tag FOP income as `Income`.
3. **Salary-anchored "this month"** — "this month" starts on the day the first salary credit arrived on a FOP account, not on calendar day 1.

## Motivation

- Money sent to Olena is a shared household expense, not Nazar's personal spending — mixing them distorts solo budget tracking.
- Calendar months don't match the real spending cycle; salary day 1 is the true reset point.
- Current categories have no `Income` bucket and no way to distinguish partner transfers from generic ATM cash.

## Acceptance criteria

- [ ] `Transaction.mode` column: `"solo" | "couple" | None`. `None` = income/cashback/internal transfer (not a spending event).
- [ ] Monobank sync auto-sets `mode`:
  - Transfers to Olena (description matches `OLENA_NAME_PATTERN` env var, case-insensitive) → `couple`
  - All other expenses → `solo`
  - Income on FOP accounts → `mode = None`
- [ ] New canonical categories: `Income`, `Couple Transfer`.
- [ ] MCC/description rules updated:
  - `Couple Transfer` = P2P transfer to Olena (detected by name pattern).
  - `Income` = positive-amount transaction on a FOP account.
- [ ] `Account.is_fop` boolean column. Set manually via a new `PATCH /accounts/{id}` endpoint or seeded via `FOP_ACCOUNT_IDS` env var (comma-separated Monobank account IDs).
- [ ] `_period_dates("this_month")` uses salary-anchored start: earliest positive transaction on any FOP account in the current calendar month. Falls back to day 1 if no salary found yet this month.
- [ ] All analytics queries (`get_spending_by_category`, `get_monthly_trend`, `get_recent_transactions`) accept optional `mode: str | None` parameter. `None` = all.
- [ ] Claude tools in `tools.py` expose the `mode` param so Nazar can ask "show couple spending this month".
- [ ] Alembic migrations for `mode` column and `is_fop` column with proper server defaults.
- [ ] Existing tests still pass; new tests cover salary-anchor logic and mode auto-assignment.

## Data model changes

### `transactions` table

```
mode  TEXT  NULL  -- "solo" | "couple" | NULL
```

Backfill: all existing negative transactions → `solo`. All positive → `NULL`.

### `accounts` table

```
is_fop  BOOLEAN  NOT NULL  DEFAULT FALSE
```

## Config changes (`Settings`)

```python
olena_name_pattern: str = "Олена|Olena|olena"  # regex alternation, case-insensitive
fop_account_ids: str = ""  # comma-separated monobank_id values; seeded on sync startup
```

## Categorization rules (in priority order)

| Priority | Condition | Category | Mode |
|---|---|---|---|
| 1 | Positive amount, account.is_fop | `Income` | `None` |
| 2 | Negative amount, description matches `olena_name_pattern` | `Couple Transfer` | `couple` |
| 3 | MCC lookup hit | existing MCC category | `solo` |
| 4 | Positive amount, not FOP | existing category or `None` | `None` |
| 5 | Fallback | `None` | `solo` (if negative) |

## Salary-anchored period logic

```python
def _salary_start_of_month(session: Session) -> date:
    """Return the date of the first FOP income this calendar month, or day 1."""
    today = date.today()
    month_start = today.replace(day=1)
    fop_account_ids = session.exec(
        select(Account.id).where(Account.is_fop == True)
    ).all()
    if not fop_account_ids:
        return month_start
    first_salary = session.exec(
        select(Transaction.date)
        .where(Transaction.account_id.in_(fop_account_ids))
        .where(Transaction.amount > 0)
        .where(Transaction.date >= month_start)
        .order_by(Transaction.date.asc())
        .limit(1)
    ).first()
    return first_salary or month_start
```

`_period_dates("this_month")` calls this instead of `today.replace(day=1)`.
`_period_dates("last_month")` similarly anchors to the first FOP credit in the previous calendar month.

## Files to change

- `finance_api/domains/transactions/categories.py` — add `INCOME`, `COUPLE_TRANSFER`
- `finance_api/domains/transactions/models.py` — add `mode` field
- `finance_api/domains/accounts/models.py` — add `is_fop` field
- `finance_api/core/config.py` — add `olena_name_pattern`, `fop_account_ids`
- `finance_api/domains/sync/monobank.py` — apply categorization priority table; seed `is_fop` from config on startup
- `finance_api/domains/insights/queries.py` — salary-anchor `_period_dates`; add `mode` param to query functions
- `finance_api/domains/insights/tools.py` — expose `mode` param in Claude tool definitions
- `finance_api/routers/accounts.py` — add `PATCH /accounts/{id}` to toggle `is_fop`
- `alembic/versions/0007_add_mode_and_is_fop.py` — migration

## Open questions

- Should `couple` expenses count against a shared budget or only appear in "couple" mode? (Defer to spec 010.)
- Olena name pattern: regex or exact substring? (Config default covers both spellings; regex is more robust.)
- Historical backfill: should the migration re-categorize existing Olena transfers, or only apply to future syncs? (Recommendation: backfill based on description pattern in the migration for completeness.)
