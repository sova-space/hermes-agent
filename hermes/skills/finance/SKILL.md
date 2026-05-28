---
name: finance
description: Query Nazar's Monobank financial data via the Finance API
metadata:
  hermes:
    tags: [finance, monobank, money, spending, accounts]
    category: finance
---

# Finance

Access to Nazar's Monobank bank data through the Finance API.

Base URL: `https://finance-api-production-4d72.up.railway.app`

Call these as HTTP tools.

## Endpoints

### GET /accounts
Returns list of `{name, currency, balance, type}` for all synced accounts.
Use when asked about balances or "how much money do I have".

### GET /transactions?limit=20
Returns recent transactions: `{date, description, amount, currency, category}`.
Negative amount = expense, positive = income.

### GET /transactions/spending?period=this_month
Returns `{category: total_spent}` for the period.

Periods: `this_month` | `last_month` | `last_7d` | `last_30d` | `last_90d`

Use for "how much did I spend on food", "show my spending breakdown".

### GET /transactions/trend?months=3
Returns `[{month, income, expenses}]` for each calendar month.
Use for "show me my monthly trend" or multi-month comparisons.

### POST /sync
Triggers a fresh Monobank sync in the background. Returns immediately.
Use when asked to refresh or sync data.

### GET /sync/status
Returns last sync run: `{status, started_at, completed_at, tx_imported, error}`.

## Rules

- Always call GET /accounts first before answering any money question.
- Amounts are in the account's currency (UAH, USD, EUR).
- If GET /accounts returns `[]`, tell Nazar to trigger a sync first.
- Full Swagger docs at `/docs` if schema details are needed.

## Telegram topic

Respond to finance questions in the `#finance` topic (thread ID configured in
`hermes/config/telegram.yaml`). Reply in-thread.
