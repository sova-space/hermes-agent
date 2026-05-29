---
name: finance
description: Handle /balance, /stats, /budget, /sync commands and answer money questions using the Monobank Finance API
metadata:
  hermes:
    tags: [finance, monobank, money, spending, accounts, budget]
    category: finance
---

# Finance

Access to Nazar's Monobank bank data. All finance replies go to the `#finance` topic.

Base URL: `https://finance-api-production-4d72.up.railway.app`

---

## Routing

If the incoming message contains `@sova_finance_bot` (e.g. `/balance@sova_finance_bot`), **do not respond** — the finance bot handles it directly. Only respond to commands that are not explicitly addressed to another bot.

---

## Commands

### /balance

Call `GET /accounts`. Format as:

```
💳 Accounts

🏦 Black (UAH)     12,340.50 ₴
💵 USD Card           234.00 $
💶 EUR Savings        156.00 €
```

Use ₴ for UAH, $ for USD, € for EUR. One line per account.

---

### /stats [period]

Default period: `this_month`. Accepted periods: `this_month` `last_month` `last_7d` `last_30d` `last_90d`.

Call `GET /transactions/spending?period=<period>&exclude_uncategorized=false`.

Format as:

```
📊 Spending — May 2026

🛒 Groceries        5,200 ₴  22%
🍔 Restaurants      3,100 ₴  13%
🏠 Housing          8,500 ₴  36%
🚇 Transport        1,200 ₴   5%
💊 Health             800 ₴   3%
👗 Clothes          2,100 ₴   9%
🎮 Entertainment      600 ₴   3%
📦 Other            1,900 ₴   8%

Total: 23,400 ₴
```

Sort by amount descending. Show percentage of total.

---

### /budget

Call `GET /budgets`.

Format as:

```
📉 Budget — May 2026

🛒 Groceries    5,200 / 6,000 ₴   ✅  800 left
🍔 Restaurants  3,100 / 2,500 ₴   ⚠️  OVER by 600
🏠 Housing      8,500 / 9,000 ₴   ✅  500 left
```

Show ✅ when under budget, ⚠️ when exceeded. Sort exceeded categories first.

---

### /budget set <category> <amount>

Call `POST /budgets` with `{"category": "<category>", "monthly_limit": <amount>}`.

Confirm with:

```
✅ Budget set: 🛒 Groceries → 6,000 ₴/month
```

Look up the emoji from the category table below before confirming.

---

### /budget delete <category>

Call `DELETE /budgets/<category>`. Confirm deletion or report if not found.

---

### /sync

Call `POST /sync` (returns immediately). Then call `GET /sync/status` and report:

```
🔄 Sync started. Last run: completed 3 min ago, 12 transactions imported.
```

---

## Category → emoji

| Category | Emoji |
|---|---|
| Groceries | 🛒 |
| Supermarket | 🛒 |
| Restaurants | 🍔 |
| Food | 🍔 |
| Outside food | 🍔 |
| Transport | 🚇 |
| Commuting | 🚇 |
| Housing | 🏠 |
| Utilities | 🏠 |
| Health | 💊 |
| Pharmacy | 💊 |
| Clothes | 👗 |
| Shopping | 🛍️ |
| Entertainment | 🎮 |
| Travel | ✈️ |
| Financial | 💳 |
| Transfers | 💸 |
| Income | 💰 |
| Salary | 💰 |
| Other | 📦 |
| Uncategorized | 📦 |

If a category isn't in the table, use 📦.

---

## General money questions

For conversational questions ("how much money do I have?", "what did I spend on food?"):

- Balance / "how much money" → `GET /accounts`
- Spending breakdown → `GET /transactions/spending?period=this_month`
- Specific category → filter from spending response
- Monthly trend → `GET /transactions/trend?months=3`
- Recent transactions → `GET /transactions?limit=20`
- Sync status → `GET /sync/status`

Always call `GET /accounts` first before answering any money question.
If `GET /accounts` returns `[]`, tell Nazar to trigger `/sync` first.

---

## Telegram topic

All finance replies go to `#finance` (topic `1192` in supergroup `-1003913424869`).
Reply in-thread.

---

## Phase 2 (not yet implemented)
- Proactive budget-exceeded alerts after each sync (needs `TELEGRAM_BOT_TOKEN` in Railway)
- `#finance` topic: thread ID 1192 ✅
