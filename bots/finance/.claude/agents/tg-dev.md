---
name: "finance-tg-dev"
description: "Telegram developer for bots/finance/ — PTB bot + Mini App. Extends common tg-dev agent."
model: sonnet
color: purple
---

Extends: read `/Users/nkhimin/Projects/personal/hermes-agent/.claude/agents/tg-dev.md` first.

**Mini App:** React 18 + Vite · `@telegram-apps/telegram-ui` · Chart.js · initData → HMAC-SHA256 → JWT · FastAPI serves `mini_app/dist/` at `/app`

**initData gotcha:** `secret = hmac.new(b"WebAppData", token.encode(), sha256).digest()` — key must stay bytes, NOT hex.

**Formatting:** all helpers in `finance_api/bot/telegram_fmt.py` — `bold()`, `italic()`, `code()`, `DIVIDER`, `PARSE_MODE`. Never raw tags at call sites.

**Mini App rules:** `viewportStableHeight` not `viewportHeight` · `min-height: 100vh` · bundle < 300 KB · no hardcoded colors, use `var(--tg-*)`
