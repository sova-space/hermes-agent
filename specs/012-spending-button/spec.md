# Spec 012 — Spending Button on /balance Keyboard

## Problem

Checking spending for the current salary cycle requires navigating to `/stats` with
arguments. The `/balance` keyboard is already open after every balance check — there is
no one-tap path from "how much do I have?" to "how much have I spent this cycle?".
The Income button already anchors to the salary cycle; Spending should mirror it.

## Solution

Add a "📊 Spending" inline button to the `/balance` keyboard. Tapping it edits the
message in place (same pattern as all other buttons) and shows a UAH-only, salary-cycle
spending breakdown grouped by category, sorted by amount descending. The keyboard stays
attached so the user can switch back to Balance/Income without issuing a new command.

## Scope

**In scope**
- New `SPENDING_CALLBACK` constant and `callback_spending` handler in `handlers.py`
- New `format_spending_summary()` formatter in `formatter.py`
- Reuse of `get_spending_by_category(period=THIS_MONTH)` with salary anchoring already
  handled inside the query
- UAH totals only — foreign-currency rows are silently dropped (they are negligible for
  personal accounts; Black/White are UAH)
- Exclusion of `COUPLE_TRANSFER` and `CASHBACK` categories from both the rows and the
  grand total (passthroughs and cashback credits are not discretionary spending)

**Out of scope**
- Category drill-down (later, separate spec)
- Foreign-currency spending aggregation / conversion
- Multi-period selector (this_month / last_month toggle)
- Budget-vs-actual overlay (already on `/budget`)
- Any change to `/stats` command behaviour

## User flow

1. User sends `/balance` — sees balance with 5-button keyboard.
2. User taps "📊 Spending".
3. Message edits to salary-cycle spending summary; keyboard remains.
4. User can tap "💳 Balance" to return to balance view, or any other button.

## Format

```
📊 Spending — May 11–Jun 4

🍔 Food & Drink    4,320 ₴   28%
🛒 Groceries       3,100 ₴   20%
🚇 Transportation  1,850 ₴   12%
🛍️ Shopping        1,600 ₴   10%
💊 Healthcare        900 ₴    6%
...

Total: 15,420 ₴
```

- Header date: `{salary_start_day} {month} – {today_day} {today_month}` (e.g. "May 11–Jun 4")
- Rows: emoji + bold category name, right-aligned amount, right-aligned percentage
- Rows with zero amount are omitted
- `COUPLE_TRANSFER` and `CASHBACK` are excluded before totalling
- If no UAH spending rows remain: show "No spending recorded yet this cycle."
- Use `pre()` block so columns align (monospaced font)

## Keyboard layout change

Current two-row layout:

```
[ 💳 Balance ]  [ 💰 Income ]  [ 👁 Skipped ]
[ 🔄 Sync    ]  [ 📊 Finance (url) ]
```

New layout — Spending fits naturally in row 1 by replacing the text label "Finance"
(which is a mini-app URL button and moves to row 2):

```
[ 💳 Balance ]  [ 💰 Income ]  [ 📊 Spending ]
[ 👁 Skipped ]  [ 🔄 Sync ]   [ 📊 Finance (url) ]
```

Row 1 stays at three buttons (all edit-in-place). Row 2 becomes three as well — Skipped
and Sync move down, Finance URL stays last.

## Success criteria

1. Tapping "📊 Spending" shows the salary-cycle UAH breakdown with correct exclusions.
2. The grand total excludes `COUPLE_TRANSFER` and `CASHBACK` amounts.
3. The period header correctly shows the salary start date (not month start).
4. All other buttons still work — no regression.
5. `ruff check` passes.

## Open questions

None. Ready for implementation.

---

## Implementation pointers for dev

**Files to touch** (all in `agents/finance/finance_api/`):

| File | Change |
|---|---|
| `domains/bot/handlers.py` | Add `SPENDING_CALLBACK = "spending"` constant. Add `callback_spending` handler (async, same pattern as `callback_income`). Register it in `runner.py`. Update `_balance_keyboard()` to the new 3+3 layout. |
| `domains/bot/formatter.py` | Add `format_spending_summary(rows: list[dict], period_start: date, today: date) -> str`. Takes the raw rows from the query, filters out `COUPLE_TRANSFER` / `CASHBACK`, formats in `pre()` block. |
| `domains/insights/queries.py` | Add `get_spending_summary() -> dict[str, Any]` — calls `get_spending_by_category(period=THIS_MONTH)` (salary anchoring is already active for `THIS_MONTH`), returns `{rows: [...], period_start: date, period_end: date}`. Needs to also return the `period_start` the same way `get_income_summary` derives it via `_salary_anchored_start`. |
| `domains/bot/runner.py` | Register `CallbackQueryHandler(callback_spending, pattern=f"^{SPENDING_CALLBACK}$")`. |

**Key existing hooks to reuse:**
- `_salary_anchored_start(start, session)` in `queries.py` — call it inside `get_spending_summary` to derive the actual cycle start date
- `_edit(query, text, ...)` in `handlers.py` — use for the edit-in-place pattern
- `_emoji(category)` and `_fmt_amount(amount, currency)` in `formatter.py`
- `COUPLE_TRANSFER` and `CASHBACK` constants from `domains/transactions/categories.py`
- `pre()` from `bot/telegram_fmt.py` for monospaced column alignment

**Exclusion logic** (in `format_spending_summary`):
```python
EXCLUDED = {cat.COUPLE_TRANSFER, cat.CASHBACK}
uah_rows = [r for r in rows if r["currency"] == "UAH" and r["category"] not in EXCLUDED]
```

**Period header** (in `format_spending_summary`):
```python
start_label = period_start.strftime("%-d %b") if period_start.month != today.month
              else period_start.strftime("%-d")
# e.g. "May 11–Jun 4" or "May 11–28" if same month
```

**No new REST endpoint needed** — `get_spending_summary` is called directly from the
handler via `asyncio.to_thread`, same as all other queries.
