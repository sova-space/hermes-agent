---
name: deploy
description: Deploy Hermes services to Railway. Covers the full topology (which project is which), the correct deploy commands for each service, and how to verify a deploy succeeded. Use whenever deploying, redeploying, or troubleshooting a Railway deployment.
model: sonnet
version: 1.0.0
---

# Deploy — Hermes Railway Topology

## Two Railway projects, one monorepo

All code lives in `sova-claw/hermes-agent`. There are **two separate Railway projects** — never mix them up:

| Service | Railway Project | Project ID | Code path |
|---|---|---|---|
| Hermes orchestrator | `hermes-main` | `3d73dc58-1201-4258-bc1d-1f9c24333032` | repo root |
| Finance sub-agent | `finance-agent` | `186cf9f1-f88f-4b73-b286-a055e107cc9d` | `agents/finance/` |

Finance project service IDs (required for `railway link`):
- `finance-api` service: `b6cb492f-9100-4330-82db-8afd95d6fe91`
- DB service: `b81eaac6-f7f1-46c4-a113-b60a39e59729`
- Environment: `de3164da-54fe-4557-ae8b-bd5d1ef01a33`

**Railway does NOT auto-deploy on git push for either service.** Always trigger manually.

---

## Deploying Hermes orchestrator

```bash
# Verify context — must show hermes-main / Hermes Agent
railway status

# Deploy from repo root
railway up --detach -m "your message"
```

---

## Deploying Finance sub-agent

```bash
# Always deploy from agents/finance/ — not repo root
cd /Users/nkhimin/Projects/personal/hermes-agent/agents/finance

# Verify context first
railway status
# Expected: Project: finance-agent, Service: finance-api

# If context is wrong, re-link:
railway link \
  --project 186cf9f1-f88f-4b73-b286-a055e107cc9d \
  --service b6cb492f-9100-4330-82db-8afd95d6fe91 \
  --environment de3164da-54fe-4557-ae8b-bd5d1ef01a33

# Deploy
railway up --detach -m "your message"
```

---

## Verifying a deployment

```bash
# Watch until SUCCESS or FAILED
until railway service status 2>&1 | grep -E "SUCCESS|FAILED|CRASHED"; do sleep 15; done
railway service status

# Check logs if FAILED
railway service logs --lines 50
```

For the Finance service, Alembic migrations run automatically on startup via `entrypoint.sh`. Check logs for migration errors before assuming a crash is a code issue.

---

## Railway CLI vs MCP

Prefer **Railway CLI** (`railway` commands above) for all deploy operations — it is more reliable and always available.

Use **Railway MCP** (`mcp__railway-mcp-server__*` tools) only when the CLI cannot do the operation (e.g., creating a new service via API). Note: the MCP server sometimes requires re-auth (`railway login`) — fall back to CLI if MCP returns Unauthorized.

---

## Rules — never do these

- **Never deploy finance from `hermes-main`** — that project has no finance service
- **Never deploy from `/Users/nkhimin/Projects/personal/hermes-finance/`** — that repo is stale and archived
- **Never create new Railway services** — both `finance-api` and `Hermes Agent` already exist
- **Never assume git push triggered a deploy** — it didn't; always run `railway up --detach`

---

## Adding a new sub-agent

New sub-agents (`agents/<name>/`) get their **own Railway project** (not added to `hermes-main` or `finance-agent`). Steps:

1. Write spec in `specs/NNN-name/spec.md`
2. Implement under `agents/<name>/` with its own `Dockerfile`, `railway.toml`, `pyproject.toml`
3. Create a new Railway project via dashboard or `railway init`
4. Link with `railway link` from `agents/<name>/`
5. Set env vars in Railway dashboard
6. Document the new project ID in CLAUDE.md and this skill
