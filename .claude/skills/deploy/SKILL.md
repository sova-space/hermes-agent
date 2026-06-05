---
name: deploy
description: Deploy Hermes services to Railway. Full topology — projects, services, build config, runtime, volumes, DBs, network, env vars, deploy commands, and health verification. Invoke whenever deploying, redeploying, or troubleshooting Railway.
model: sonnet
version: 1.2.0
---

# Hermes Railway Topology

All code lives in `sova-claw/hermes-agent` at `/Users/nkhimin/Projects/personal/hermes-agent`.

**Railway does NOT auto-deploy on git push.** Always trigger manually with `railway up --detach`.

---

## Projects at a glance

| Component | Railway Project | Project ID | Code path |
|---|---|---|---|
| Hermes orchestrator | `hermes-main` | `3d73dc58-1201-4258-bc1d-1f9c24333032` | repo root |
| Finance sub-agent | `hermes-main` | `3d73dc58-1201-4258-bc1d-1f9c24333032` | `bots/finance/` |

Both services live in the same Railway project `hermes-main`. The old `finance-agent` project (`186cf9f1`) is decommissioned.

---

## hermes-main

### Build
| Field | Value |
|---|---|
| Builder | Dockerfile |
| Dockerfile | `infra/Dockerfile` |
| Build context | repo root |
| Config file | `railway.toml` (repo root) |
| Start command | `/app/start.sh` |
| Health check | `GET /health` — timeout 300 s |

`infra/Dockerfile` installs the Hermes runtime, pre-builds the React dashboard and TUI, copies skills/plugins/config into `/app/`.

### Services
| Name | Service ID | Public URL |
|---|---|---|
| Hermes Agent | `8d1fc2f6-031b-4527-9a7d-3e78316d1180` | `hermes-agent-production-d21c.up.railway.app` |

### Volumes
| Volume | ID | Mount | Size |
|---|---|---|---|
| `hermes-agent-volume` | `1f3ffc13-311b-4026-a774-4f7101157a91` | `/data` | 5 GB |

Agent state at `/data/.hermes`. Config seeded from `/app/config/` on every boot. Cookie auth secret regenerates on restart — redeploy invalidates sessions.

### Env vars (required)
```
PORT                         # web server port
ADMIN_USERNAME
ADMIN_PASSWORD
OPENROUTER_API_KEY
LLM_MODEL                    # e.g. openai/gpt-4o-mini
TELEGRAM_BOT_TOKEN
TELEGRAM_ALLOWED_USER_IDS
SLACK_BOT_TOKEN
SLACK_APP_TOKEN
HERMES_GITHUB_PAT            # PAT for self-update PRs
RAILWAY_PROJECT_ID           # 3d73dc58-... (used by server.py to self-manage)
AGENT_REPO                   # https://github.com/sova-claw/hermes-agent.git
```

### Deploy
```bash
# From repo root — verify context first
railway status
# Expected: Project: hermes-main, Service: Hermes Agent

railway up --detach -m "your message"
```

---

## hermes-finance (finance sub-agent)

### Build
| Field | Value |
|---|---|
| Builder | Dockerfile |
| Dockerfile | `Dockerfile` (at `bots/finance/`) |
| Build context | `bots/finance/` |
| Config file | `railway.toml` (at `bots/finance/`) |
| Start command | `sh entrypoint.sh` |
| Health check | `GET /health` — timeout 60 s |

`entrypoint.sh` runs `alembic upgrade head` before starting the FastAPI server. Migration errors crash the service before it ever accepts traffic.

### Services
| Name | Service ID | Role | Public URL |
|---|---|---|---|
| `hermes-finance` | `9bc27c48-c35d-4dcf-9f4e-ba3c73e1ed96` | FastAPI + PTB + APScheduler | `hermes-finance-production.up.railway.app` |
| `Postgres` | `b6daf7a2-de33-4767-a78b-e4e4d7424d58` | PostgreSQL 16 | internal only |

Environment: `production` (`a2a88403-f2b1-4a18-a44d-3b808d07bcb1`)

### Volumes
| Volume | Mount | Size | Attached to |
|---|---|---|---|
| `postgres-volume` | `/var/lib/postgresql/data` | 5 GB | Postgres service |

### Network (internal)
```
hermes-finance → Postgres
  Host:     postgres.railway.internal
  Port:     5432
  Database: railway
  Var:      DATABASE_URL  (postgresql+psycopg://user:pass@postgres.railway.internal:5432/railway)
```

### Env vars
```
# Required — already set in production
DATABASE_URL               # Railway reference variable → Postgres service
MONOBANK_TOKEN             # Monobank API token for sync
TELEGRAM_BOT_TOKEN         # @sova_finance_bot token
MINI_APP_URL               # https://hermes-finance-production.up.railway.app/miniapp
PORT                       # 8000
ENVIRONMENT                # production
LOG_LEVEL                  # INFO
MONOBANK_FETCH_DAYS        # 730
SYNC_INTERVAL_HOURS        # 1
TELEGRAM_OWNER_ID          # Nazar's Telegram user ID

# Have defaults — override if needed
TELEGRAM_CHAT_ID           # -1003913424869
TELEGRAM_FINANCE_TOPIC_ID  # 1192 (Telegram topic: #finance)

# Optional — spec 009 spending modes
PARTNER_NAME_PATTERN       # regex, default: "Олена|Olena|olena"
FOP_ACCOUNT_IDS            # comma-separated Monobank account IDs of salary/FOP accounts
```

### Deploy
```bash
# Must be at bots/finance/ — railway up uses local dir as build context
cd /Users/nkhimin/Projects/personal/hermes-agent/bots/finance

# Verify context (should show hermes-main / hermes-finance)
railway status

# If wrong, re-link:
railway link \
  --project 3d73dc58-1201-4258-bc1d-1f9c24333032 \
  --service 9bc27c48-c35d-4dcf-9f4e-ba3c73e1ed96 \
  --environment a2a88403-f2b1-4a18-a44d-3b808d07bcb1

railway up --detach -m "your message"
```

---

## Verifying a deployment

```bash
# Poll until terminal status
until railway service status 2>&1 | grep -E "SUCCESS|FAILED|CRASHED"; do sleep 15; done
railway service status

# Logs — always check on FAILED
railway service logs --lines 100

# Finance: confirm Alembic ran cleanly
railway service logs --lines 100 | grep -iE "alembic|migration|error|traceback"
```

### Health check URLs
```
Hermes Agent:   https://hermes-agent-production-d21c.up.railway.app/health
Finance API:    https://hermes-finance-production.up.railway.app/health
```

---

## Redeploy without code change

```bash
railway service redeploy
```

Use when you changed env vars, want a fresh container, or need to re-run Alembic.

---

## Railway CLI reference

```bash
railway status                      # current linked project/service
railway service status              # deployment status + ID
railway service logs --lines N      # runtime logs
railway service logs --tail         # follow logs live
railway service redeploy            # redeploy latest image (no upload)
railway variable list               # all env vars for linked service
railway variable set KEY=value      # set one or more vars
railway up --detach -m "msg"        # build + deploy from local code
railway link --project ID \
  --service ID --environment ID     # re-link to a specific service
```

**MCP tools** (`mcp__railway-mcp-server__*`) — use only when CLI can't do the operation. MCP requires periodic re-auth; fall back to CLI if it returns Unauthorized.

---

## Hard rules

- **Finance IS in `hermes-main`** — link to project `3d73dc58`, service `9bc27c48`
- **Deploy finance from `bots/finance/`** — `railway up` uses local dir as build context; running from repo root uploads the wrong Dockerfile
- **Never deploy from `/Users/nkhimin/Projects/personal/hermes-finance/`** — stale archived repo
- **Never create new services in existing projects** — all services already exist in `hermes-main`
- **Never assume git push triggered a deploy** — it never does; always run `railway up --detach`
- **Secrets in Railway Variables only** — never in code, never committed

---

## Adding a new sub-agent

Each new `bots/<name>/` gets its **own Railway project**. Never add to `hermes-main` or `finance-agent`.

1. Write spec: `specs/NNN-name/spec.md`
2. Implement `bots/<name>/` with its own `Dockerfile`, `railway.toml`, `pyproject.toml`, `uv.lock`
3. `cd bots/<name>/ && railway init --name <name>-agent`
4. Add PostgreSQL via dashboard if the agent needs a DB
5. Set `DATABASE_URL` as a reference variable pointing to the new Postgres
6. Set all required env vars in the Railway dashboard
7. `railway up --detach`
8. **Update CLAUDE.md and this skill** with the new project ID + service IDs — mandatory before closing the PR
