---
name: finance
description: Answer conversational money questions using the Monobank Finance API. Do NOT handle /balance, /stats, /budget, or /sync slash commands — those belong to @sova_finance_bot.
metadata:
  hermes:
    tags: [finance, monobank, money, spending, accounts, budget]
    category: finance
---

# Finance

Access to Nazar's Monobank bank data via the Finance API.

Base URL: `https://finance-api-production-4d72.up.railway.app`

---

## Routing — read this first

**Slash commands** (`/balance`, `/stats`, `/budget`, `/sync`) — handled exclusively by `@sova_finance_bot`. **Do not respond.** Stay completely silent if you see any of these.

**Commands addressed to another bot** (e.g. `/balance@sova_finance_bot`) — **do not respond**. That bot handles it.

**Finance questions from topics other than `#finance` (thread 1192)** — reply in `#finance` (topic 1192) and ask the user to use that channel for finance queries.

Only respond to **conversational questions** about money asked in `#finance`:
- "how much money do I have?"
- "what did I spend on food this month?"
- "am I over budget?"
- "when was the last sync?"

---

## API calls

| Question | Endpoint |
|----------|----------|
| Balance / "how much money" | `GET /accounts` |
| Spending breakdown | `GET /transactions/spending?period=this_month` |
| Specific category | filter from spending response |
| Monthly trend | `GET /transactions/trend?months=3` |
| Recent transactions | `GET /transactions?limit=20` |
| Budget status | `GET /budgets` |
| Sync status | `GET /sync/status` |

Always call `GET /accounts` first before answering any money question.
If `GET /accounts` returns `[]`, tell Nazar to run `/sync@sova_finance_bot` first.

---

## Category → emoji

| Category | Emoji |
|---|---|
| Groceries | 🛒 |
| Restaurants | 🍔 |
| Transport | 🚇 |
| Housing | 🏠 |
| Health | 💊 |
| Clothes | 👗 |
| Shopping | 🛍️ |
| Entertainment | 🎮 |
| Travel | ✈️ |
| Financial | 💳 |
| Transfers | 💸 |
| Income | 💰 |
| Other | 📦 |

---

## Telegram channel

All finance replies go to `#finance` (topic `1192` in supergroup `-1003913424869`). Reply in-thread.
