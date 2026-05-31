---
name: deploy
description: Deploy Hermes services to Railway. Covers the full topology — projects, services, volumes, DBs, env vars, deploy commands, and health verification. Invoke whenever deploying, redeploying, or troubleshooting Railway.
model: sonnet
version: 1.1.0
---

# Deploy — Hermes Railway Topology

## Two Railway projects, one monorepo

All code is in `sova-claw/hermes-agent` at `/Users/nkhimin/Projects/personal/hermes-agent`.

| Component | Railway Project | Project ID | Code path |
|---|---|---|---|
| Hermes orchestrator | `hermes-main` | `3d73dc58-1201-4258-bc1d-1f9c24333032` | repo root |
| Finance sub-agent | `finance-agent` | `186cf9f1-f88f-4b73-b286-a055e107cc9d` | `agents/finance/` |

**Railway does NOT auto-deploy on git push.** Always trigger manually with `railway up --detach`.

---

## hermes-main — services, volumes, env vars

### Services
| Name | Service ID | URL |
|---|---|---|
| Hermes Agent | `8d1fc2f6-031b-4527-9a7d-3e78316d1180` | `hermes-agent-production-d21c.up.railway.app` |

### Volumes
| Volume | Mount | Size |
|---|---|---|
| `hermes-agent-volume` | `/data` | 5 GB |

Agent state lives at `/data/.hermes`. Config seeded from `/app/config/` on every boot.

### Required env vars
```
PORT                       # web server port
ADMIN_USERNAME / ADMIN_PASSWORD
OPENROUTER_API_KEY
LLM_MODEL                  # e.g. openai/gpt-4o-mini
TELEGRAM_BOT_TOKEN
TELEGRAM_ALLOWED_USER_IDS
SLACK_BOT_TOKEN / SLACK_APP_TOKEN
HERMES_GITHUB_PAT
```

### Deploy
```bash
# Must be at repo root; verify context first
railway status
# Expected: Project: hermes-main, Service: Hermes Agent

railway up --detach -m "your message"
```

---

## finance-agent — services, volumes, env vars

### Services
| Name | Service ID | Role |
|---|---|---|
| `finance-api` | `b6cb492f-9100-4330-82db-8afd95d6fe91` | FastAPI + aiogram + APScheduler |
| `Postgres` | `b81eaac6-f7f1-46c4-a113-b60a39e59729` | PostgreSQL 16 |

Environment ID: `de3164da-54fe-4557-ae8b-bd5d1ef01a33`

### Volumes
| Volume | Mount | Size | Service |
|---|---|---|---|
| `postgres-volume` | `/var/lib/postgresql/data` | 5 GB | Postgres |

### DB connection (internal)
```
Host:     postgres.railway.internal
Port:     5432
Database: railway
URL env:  DATABASE_URL (postgresql+psycopg://...)
```
Alembic runs `alembic upgrade head` automatically on startup via `entrypoint.sh`.

### Required env vars (already set in production)
```
DATABASE_URL               # set by Railway reference to Postgres service
MONOBANK_TOKEN             # Monobank API token
TELEGRAM_BOT_TOKEN         # @sova_finance_bot token
PORT                       # 8000
ENVIRONMENT                # production
LOG_LEVEL                  # INFO
MONOBANK_FETCH_DAYS        # 730
SYNC_INTERVAL_HOURS        # 1
TELEGRAM_CHAT_ID           # -1003913424869 (default)
TELEGRAM_FINANCE_TOPIC_ID  # 1192 (default)
```

### Optional env vars (spec 009)
```
PARTNER_NAME_PATTERN       # regex for partner transfers, default: "Олена|Olena|olena"
FOP_ACCOUNT_IDS            # comma-separated Monobank IDs of FOP/salary accounts
```

### Deploy
```bash
# Must be at agents/finance/; verify context first
cd /Users/nkhimin/Projects/personal/hermes-agent/agents/finance
railway status
# Expected: Project: finance-agent, Service: finance-api

# If context is wrong, re-link:
railway link \
  --project 186cf9f1-f88f-4b73-b286-a055e107cc9d \
  --service b6cb492f-9100-4330-82db-8afd95d6fe91 \
  --environment de3164da-54fe-4557-ae8b-bd5d1ef01a33

railway up --detach -m "your message"
```

---

## Verifying a deployment

```bash
# Poll until terminal status
until railway service status 2>&1 | grep -E "SUCCESS|FAILED|CRASHED"; do sleep 15; done
railway service status

# Tail logs (use after FAILED or to watch startup)
railway service logs --lines 80

# Finance: check Alembic ran
railway service logs --lines 80 | grep -E "alembic|migration|ERROR"
```

Health endpoints:
- Hermes Agent: `GET /health`
- Finance API: `GET /health`

---

## Railway CLI vs MCP

**Always prefer CLI.** It is faster and always authed.

```bash
railway status           # current context
railway service status   # deployment status
railway service logs     # runtime logs
railway variable list    # env vars
railway up --detach      # deploy
```

**MCP** (`mcp__railway-mcp-server__*`) only when CLI can't do it (e.g. creating a service programmatically). MCP requires re-auth occasionally — if it returns Unauthorized, fall back to CLI and ask user to `railway login`.

---

## Hard rules

- **Never deploy finance from `hermes-main`** — it has no finance service
- **Never deploy from `/Users/nkhimin/Projects/personal/hermes-finance/`** — stale, archived repo
- **Never create new Railway services** — both already exist; creating duplicates breaks billing and routing
- **Never assume git push triggered a deploy** — it never does; always run `railway up --detach`
- **Secrets stay in Railway Variables** — never in code or committed files

---

## Adding a new sub-agent

New agents (`agents/<name>/`) get their **own Railway project**, never added to `hermes-main` or `finance-agent`.

1. Write spec: `specs/NNN-name/spec.md`
2. Implement under `agents/<name>/` with its own `Dockerfile`, `railway.toml`, `pyproject.toml`, `uv.lock`
3. Create new Railway project: `railway init --name <name>-agent`
4. From `agents/<name>/`: `railway link` then `railway up --detach`
5. Add PostgreSQL service if needed; set `DATABASE_URL` reference variable
6. Document the new project ID + service IDs in **both** `CLAUDE.md` and this skill
