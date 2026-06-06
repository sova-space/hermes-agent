---
name: "doer-devops"
description: "DevOps for bots/doer/. Extends common devops agent."
model: sonnet
color: orange
---

Extends: read `/Users/nkhimin/Projects/personal/hermes-agent/.claude/agents/common/devops.md` first.

| | |
|---|---|
| Service | `hermes-doer` · `7d03d34c-4f91-496c-a30e-eef05dc8ac26` |
| Project | `hermes-main` · `3d73dc58-1201-4258-bc1d-1f9c24333032` |
| Environment | `production` · `a2a88403-f2b1-4a18-a44d-3b808d07bcb1` |
| Public URL | `https://hermes-doer-production.up.railway.app` |

```bash
cd bots/doer && env -u RAILWAY_TOKEN railway link --project 3d73dc58 --service 7d03d34c --environment a2a88403 -w aa8bb567-086d-4329-8667-89b73cb08d03
env -u RAILWAY_TOKEN railway up --detach -m "msg"
```

**Note:** always prefix railway commands with `env -u RAILWAY_TOKEN` — the project-scoped token in the env conflicts with user auth.

**Required vars:** `DOER_BOT_TOKEN` · `OPENROUTER_API_KEY` · `GITHUB_TOKEN` · `PORT` · `ENVIRONMENT` · `LOG_LEVEL`

**Root directory:** must be set to `bots/doer` in Railway dashboard → Service Settings → Source.

**Agent loop:** uses OpenRouter (`https://openrouter.ai/api/v1`) with model `anthropic/claude-sonnet-4-5`. On tool errors check `GITHUB_TOKEN` permissions (needs Contents + Pull requests read/write on target repos).
