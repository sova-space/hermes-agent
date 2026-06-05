---
name: "new-bot"
description: "Scaffold a new Telegram bot sub-project under bots/. Use when adding a new bot to the Hermes ecosystem."
model: sonnet
color: yellow
---

Follow these steps in order. Don't skip — each unblocks the next.

## 1. Scaffold files

Copy structure from `bots/wishlist/` (simplest existing bot):
```
bots/<name>/
  <name>_api/
    main.py          # app = create_app()
    composition.py   # FastAPI factory + lifespan
    core/config.py   # Settings (DATABASE_URL, TELEGRAM_BOT_TOKEN, ...)
    core/db/engine.py
    core/logging/setup.py
    domains/bot/commands.py   # BOT_COMMANDS + setup_bot()
    domains/bot/runner.py     # create_bot()
    domains/bot/handlers.py
    routers/health.py         # GET /health → {"status": "ok"}
    routers/miniapp.py        # GET /bot/commands
  alembic/env.py
  alembic.ini
  Dockerfile
  railway.toml
  entrypoint.sh     # alembic upgrade head → gunicorn
  gunicorn.conf.py
  pyproject.toml
  uv.lock           # generated: uv lock
```

## 2. Create bot in BotFather

`/newbot` → get token → keep it for step 4. Never commit it.

## 3. Create Railway service

```bash
# In Railway dashboard: hermes-main project → New Service → GitHub repo
# Set Root Directory: bots/<name>
# OR use CLI (link to hermes-main first):
railway add --service <name>
```

Add `<name>` database on shared Postgres service:
```sql
CREATE DATABASE <name>;
```
Add `<NAME>_DATABASE_URL` variable to the Postgres service pointing to the new DB.

## 4. Set env vars on the new service

```bash
railway variable set \
  DATABASE_URL='${{Postgres.<NAME>_DATABASE_URL}}' \
  TELEGRAM_BOT_TOKEN=<token-from-step-2> \
  BOT_USERNAME=<bot_username> \
  PORT=8000 \
  ENVIRONMENT=production \
  LOG_LEVEL=INFO
```

## 5. Create `.claude/agents/` package

```
bots/<name>/.claude/agents/
  <name>-product.md   # extends .claude/agents/common/product.md
  <name>-dev.md       # extends .claude/agents/common/dev.md
  <name>-devops.md    # extends .claude/agents/common/devops.md
  <name>-tg-dev.md    # extends .claude/agents/common/tg-dev.md
```

Copy from `bots/wishlist/.claude/agents/`, replace `wishlist` → `<name>`, fill in Railway IDs.

## 6. Update CLAUDE.md

Add row to the Railway topology table:
```
| <name> bot | `hermes-<name>` | `<service-id>` | `bots/<name>` |
```

Add watch pattern and link command.

## 7. First deploy

```bash
cd bots/<name>
uv lock
git add bots/<name>/
git commit -m "feat(<name>): initial scaffold"
git push origin main   # auto-deploy triggers
```

Watch: `railway service logs --latest --lines 50 --service hermes-<name>`

## Done when

- `GET /health` returns `{"status": "ok"}`
- Bot responds to `/start` in Telegram
- Alembic migration ran clean (check logs)
