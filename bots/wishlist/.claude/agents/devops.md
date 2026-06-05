---
name: "wishlist-devops"
description: "DevOps for bots/wishlist/. Extends common devops agent."
model: sonnet
color: orange
---

Extends: read `/Users/nkhimin/Projects/personal/hermes-agent/.claude/agents/common/devops.md` first.

| | |
|---|---|
| Service | `hermes-wishlist` · `7764e517-0cc2-4378-894f-d4d82570339d` |
| Project | `hermes-main` · `3d73dc58-1201-4258-bc1d-1f9c24333032` |
| Environment | `production` · `a2a88403-f2b1-4a18-a44d-3b808d07bcb1` |
| DB | `Postgres` `b6daf7a2`, database: `wishlist` |

```bash
cd bots/wishlist && railway link --project 3d73dc58 --service 7764e517 --environment a2a88403
railway up --detach -m "msg"
```

**Required vars:** `DATABASE_URL` (`${{Postgres.WISHLIST_DATABASE_URL}}`) · `TELEGRAM_BOT_TOKEN` · `BOT_USERNAME=sova_wishlist_bot` · `OPENROUTER_API_KEY` · `PORT` · `ENVIRONMENT` · `LOG_LEVEL`
