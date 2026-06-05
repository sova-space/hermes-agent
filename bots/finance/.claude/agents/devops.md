---
name: "finance-devops"
description: "DevOps for bots/finance/. Extends common devops agent."
model: sonnet
color: orange
memory: project
---

Extends: read `/Users/nkhimin/Projects/personal/hermes-agent/.claude/agents/devops.md` first.

| | |
|---|---|
| Service | `hermes-finance` · `9bc27c48-c35d-4dcf-9f4e-ba3c73e1ed96` |
| Project | `hermes-main` · `3d73dc58-1201-4258-bc1d-1f9c24333032` |
| Environment | `production` · `a2a88403-f2b1-4a18-a44d-3b808d07bcb1` |
| URL | `hermes-finance-production.up.railway.app` |
| DB | `Postgres` `b6daf7a2`, database: `railway` |

```bash
cd bots/finance && railway link --project 3d73dc58 --service 9bc27c48 --environment a2a88403
railway up --detach -m "msg"
```

**Required vars:** `DATABASE_URL` · `MONOBANK_TOKEN` · `TELEGRAM_BOT_TOKEN` · `TELEGRAM_OWNER_ID` · `PORT` · `ENVIRONMENT` · `LOG_LEVEL` · `MONOBANK_FETCH_DAYS` · `SYNC_INTERVAL_HOURS`

`entrypoint.sh` runs `alembic upgrade head` — migration errors crash before service starts.
