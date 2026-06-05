---
name: ideate-features
description: Brainstorm and prioritize new features for bots/finance. Use when the user asks what to build next or wants ideas for a specific area.
---

Stack: FastAPI + aiogram + APScheduler + PostgreSQL + Matplotlib. Monobank sync via `/domains/sync/`. Charts via `charts.py` → tmp PNG. Telegram bot with inline keyboards + Mini App.

Ask first: **"What area — data visibility, automation, UX, or integrations?"**

Then produce 3–5 ideas in this format:

```
### [Name]
What: one sentence.
Why: why it matters.
Effort: Small (<1d) / Medium (1–3d) / Large (1w+)
Where: files to touch.
```

## Idea areas

**Data visibility** — spending streaks, FX exposure (UAH vs USD/EUR), cashback tracker, per-merchant totals, savings rate

**Automation** — MCC → auto-category rules, budget alert when category exceeds threshold, salary detection (large recurring income), weekly summary pushed to Telegram

**UX** — date range picker in Mini App, transaction search, export to CSV, split transaction across categories

**Integrations** — PrivatBank sync (same pattern as Monobank), Wise API for USD/EUR accounts, Google Sheets monthly export

After presenting ideas: **"Want me to start on any of these now?"**
